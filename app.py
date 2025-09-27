from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import openpyxl
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Archivo donde se guardan los datos
DATOS_FILE = 'datos.json'

def leer_excel_y_convertir(archivo_excel):
    """Convierte el Excel a formato JSON usando openpyxl"""
    try:
        workbook = openpyxl.load_workbook(archivo_excel)
        
        datos = {
            'fecha_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tfn': [],
            'tfn_cncaf': [],
            'tfn_cncaf_csjn': []
        }
        
        # Procesar cada hoja
        sheet_mapping = {
            'TFN': 'tfn',
            'TFN_CNCAF': 'tfn_cncaf', 
            'TFN_CNCAF_CSJN': 'tfn_cncaf_csjn'
        }
        
        for sheet_name, data_key in sheet_mapping.items():
            if sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                
                # Leer headers (primera fila)
                headers = []
                for cell in sheet[1]:
                    headers.append(cell.value or '')
                
                # Leer datos (desde fila 2 en adelante)
                sheet_data = []
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if any(cell for cell in row if cell):  # Si la fila tiene datos
                        row_dict = {}
                        for i, value in enumerate(row):
                            if i < len(headers) and headers[i]:
                                row_dict[headers[i]] = str(value) if value is not None else ''
                        if row_dict:  # Solo agregar si tiene datos
                            sheet_data.append(row_dict)
                
                datos[data_key] = sheet_data
        
        return datos
        
    except Exception as e:
        raise Exception(f"Error procesando Excel: {str(e)}")

@app.route('/')
def home():
    return "Backend del Boletín de Trazabilidad funcionando correctamente"

@app.route('/admin')
def admin():
    """Página simple para subir archivos"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin - Boletín de Trazabilidad</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
            .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; border-radius: 10px; }
            button { background: #007cba; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #005a8b; }
            .status { margin: 20px 0; padding: 15px; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .info { background: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }
        </style>
    </head>
    <body>
        <h1>Panel de Administración</h1>
        <h2>Boletín de Trazabilidad de Sentencias</h2>
        
        <div class="upload-area">
            <h3>Subir archivo Excel</h3>
            <p>Selecciona el archivo Excel con las 3 hojas: TFN, TFN_CNCAF, TFN_CNCAF_CSJN</p>
            <input type="file" id="fileInput" accept=".xlsx,.xls" style="margin: 10px;">
            <br><br>
            <button onclick="subirArchivo()">Actualizar Boletín</button>
        </div>
        
        <div id="status"></div>
        
        <div style="margin-top: 30px;">
            <h3>Enlaces útiles:</h3>
            <p><a href="/api/datos" target="_blank">Ver datos JSON</a></p>
            <p><strong>URL del boletín para empleados:</strong><br>
            <code>https://TU-USUARIO.github.io/TU-REPOSITORIO</code></p>
        </div>
        
        <script>
            function subirArchivo() {
                const fileInput = document.getElementById('fileInput');
                const statusDiv = document.getElementById('status');
                
                if (!fileInput.files[0]) {
                    statusDiv.innerHTML = '<div class="error">Por favor selecciona un archivo</div>';
                    return;
                }
                
                const formData = new FormData();
                formData.append('archivo', fileInput.files[0]);
                
                statusDiv.innerHTML = '<div class="info">Procesando archivo...</div>';
                
                fetch('/api/subir', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        statusDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                    } else {
                        statusDiv.innerHTML = `<div class="success">
                            ✓ Archivo procesado exitosamente<br>
                            Fecha: ${data.fecha_actualizacion}<br>
                            TFN: ${data.total_tfn} registros<br>
                            TFN-CNCAF: ${data.total_tfn_cncaf} registros<br>
                            TFN-CNCAF-CSJN: ${data.total_tfn_cncaf_csjn} registros
                        </div>`;
                        fileInput.value = '';
                    }
                })
                .catch(error => {
                    statusDiv.innerHTML = `<div class="error">Error de conexión: ${error}</div>`;
                });
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/subir', methods=['POST'])
def subir_archivo():
    """Endpoint para subir y procesar el Excel"""
    try:
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se encontró archivo'}), 400
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        if not archivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Solo se permiten archivos Excel (.xlsx, .xls)'}), 400
        
        # Procesar Excel
        datos = leer_excel_y_convertir(archivo)
        
        # Guardar en archivo JSON
        with open(DATOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        # Respuesta con estadísticas
        return jsonify({
            'mensaje': 'Archivo procesado exitosamente',
            'fecha_actualizacion': datos['fecha_actualizacion'],
            'total_tfn': len(datos['tfn']),
            'total_tfn_cncaf': len(datos['tfn_cncaf']),
            'total_tfn_cncaf_csjn': len(datos['tfn_cncaf_csjn'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/datos')
def obtener_datos():
    """Endpoint que devuelve los datos para el frontend"""
    try:
        if not os.path.exists(DATOS_FILE):
            return jsonify({'error': 'No hay datos disponibles. Sube un archivo Excel primero.'}), 404
        
        with open(DATOS_FILE, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        return jsonify(datos)
        
    except Exception as e:
        return jsonify({'error': f'Error cargando datos: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)