from flask import Flask, request, render_template
import sqlite3
import markdown 
import os
from groq import Groq 
import docx
from PyPDF2 import PdfReader

app = Flask(__name__)

# Configuración Render
api_key = os.environ.get("GROQ_API_KEY")
cliente_groq = Groq(api_key=api_key)

def inicializar_bd():
    conexion = sqlite3.connect('base_datos.db')
    cursor = conexion.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_archivo TEXT,
            pregunta TEXT,
            respuesta TEXT
        )
    ''')
    conexion.commit()
    conexion.close()


inicializar_bd()

def extraer_texto_pdf(archivo):
    lector = PdfReader(archivo)
    texto = ""
    for pagina in lector.pages:
        if pagina.extract_text():
            texto += pagina.extract_text() + "\n"
    return texto

def extraer_texto_word(archivo):
    doc = docx.Document(archivo)
    texto = "\n".join([parrafo.text for parrafo in doc.paragraphs])
    return texto

@app.route('/', methods=['GET', 'POST'])
def inicio():
    respuesta_ia = None

    if request.method == 'POST':
        archivo = request.files['archivo']
        pregunta = request.form['pregunta']

        if archivo:
            nombre = archivo.filename.lower()
            texto_documento = ""

            # Identificar formato y extraer texto
            if nombre.endswith('.pdf'):
                texto_documento = extraer_texto_pdf(archivo)
            elif nombre.endswith('.docx'):
                texto_documento = extraer_texto_word(archivo)
            else:
                return render_template('index.html', respuesta="⚠️ Por favor, sube únicamente un archivo PDF o Word (.docx).")
            
            
            texto_recortado = texto_documento[:15000]
            
            # Instrucciones lectura de texto
            instruccion = f"""
            Actúa como un asistente experto en análisis de documentos. 
            Aquí tienes el contenido extraído del documento del usuario:
            
            {texto_recortado}
            
            Pregunta del usuario: {pregunta}
            
            Analiza el texto y responde a la pregunta basándote estrictamente en el documento proporcionado. Responde en español usando formato Markdown (con tablas, listas o negritas si ayuda a estructurar la información).
            """
            
            # respuesta con Groq
            chat_completion = cliente_groq.chat.completions.create(
                messages=[{"role": "user", "content": instruccion}],
                model="llama-3.3-70b-versatile", 
            )
            
            texto_crudo = chat_completion.choices[0].message.content

            
            respuesta_ia = markdown.markdown(texto_crudo, extensions=['tables'])

            conexion = sqlite3.connect('base_datos.db')
            cursor = conexion.cursor()
            cursor.execute(
                'INSERT INTO historial (nombre_archivo, pregunta, respuesta) VALUES (?, ?, ?)',
                (archivo.filename, pregunta, respuesta_ia)
            )
            conexion.commit()
            conexion.close()

    return render_template('index.html', respuesta=respuesta_ia)

if __name__ == '__main__':
    app.run(debug=True)