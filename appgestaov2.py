import os
import shutil
from datetime import datetime
import streamlit as st

BASE_DIR = "uploads"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# Função para criar caminho com estrutura hierárquica
def get_project_path(project, discipline, phase):
    path = os.path.join(BASE_DIR, project, discipline, phase)
    os.makedirs(path, exist_ok=True)
    return path

# Função de versionamento automático
def save_versioned_file(file_path):
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(file_path)
        versioned_path = f"{base}_v{timestamp}{ext}"
        shutil.move(file_path, versioned_path)

# Upload de arquivos
st.title("Gerenciador de Documentos Inteligente (GDI)")
st.markdown("### Upload de Arquivos")

with st.form("upload_form"):
    project = st.text_input("Projeto")
    discipline = st.text_input("Disciplina")
    phase = st.text_input("Fase")
    uploaded_file = st.file_uploader("Escolha o arquivo")
    submitted = st.form_submit_button("Enviar")

    if submitted and uploaded_file:
        filename = uploaded_file.name
        path = get_project_path(project, discipline, phase)
        file_path = os.path.join(path, filename)
        save_versioned_file(file_path)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        st.success(f"Arquivo '{filename}' salvo com sucesso em {path}.")

# Pesquisa de arquivos
st.markdown("### Pesquisa de Documentos")
keyword = st.text_input("Buscar por palavra-chave")
if keyword:
    matched_files = []
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if keyword.lower() in file.lower():
                matched_files.append(os.path.join(root, file))

    if matched_files:
        st.markdown("#### Resultados da busca:")
        for file in matched_files:
            relative_path = os.path.relpath(file, BASE_DIR)
            st.write(f"📄 {relative_path}")
            with open(file, "rb") as f:
                if file.endswith(".pdf"):
                    st.download_button(label="📥 Baixar PDF", data=f, file_name=os.path.basename(file), mime="application/pdf")
                elif file.endswith(('.png', '.jpg', '.jpeg')):
                    st.image(f.read(), caption=os.path.basename(file))
                    f.seek(0)
                    st.download_button(label="📥 Baixar Imagem", data=f, file_name=os.path.basename(file))
                else:
                    st.download_button(label="📥 Baixar Arquivo", data=f, file_name=os.path.basename(file))
    else:
        st.warning("Nenhum arquivo encontrado com esse termo.")

# Autenticação básica (simples para protótipo)
st.sidebar.markdown("### Acesso Restrito")
password = st.sidebar.text_input("Senha", type="password")
if password != "admin123":
    st.warning("Acesso restrito. Informe a senha correta na barra lateral.")
    st.stop()
