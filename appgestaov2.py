import os
import shutil
import smtplib
from datetime import datetime
import streamlit as st
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Banco de dados SQLite
conn = sqlite3.connect('document_manager.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, email TEXT, projects TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS logs (timestamp TEXT, user TEXT, action TEXT, file TEXT)''')
conn.commit()

# Parâmetros de envio de e-mail (substituir com credenciais reais)
EMAIL_FROM = "seu_email@provedor.com"
EMAIL_PASSWORD = "sua_senha"
EMAIL_SMTP = "smtp.provedor.com"
EMAIL_PORT = 587

# Envio de e-mail após upload
def enviar_email_upload(usuario, arquivo, projeto):
    c.execute("SELECT email FROM users WHERE instr(projects, ?) > 0", (projeto,))
    destinatarios = [row[0] for row in c.fetchall() if row[0]]
    if not destinatarios:
        return
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = ", ".join(destinatarios)
        msg['Subject'] = f"[Projeto {projeto}] Novo upload de {usuario}"
        body = f"O usuário {usuario} realizou o upload do arquivo '{arquivo}' no projeto '{projeto}'."
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(EMAIL_SMTP, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        st.warning(f"Erro ao enviar e-mail: {e}")

BASE_DIR = "uploads"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

def get_project_path(project, discipline, phase):
    path = os.path.join(BASE_DIR, project, discipline, phase)
    os.makedirs(path, exist_ok=True)
    return path

def save_versioned_file(file_path):
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(file_path)
        versioned_path = f"{base}_v{timestamp}{ext}"
        shutil.move(file_path, versioned_path)

def log_action(user, action, file):
    c.execute("INSERT INTO logs (timestamp, user, action, file) VALUES (?, ?, ?, ?)",
              (datetime.now().isoformat(), user, action, file))
    conn.commit()

st.title("Gerenciador de Documentos Inteligente")
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "registration_mode" not in st.session_state:
    st.session_state.registration_mode = False
if "registration_unlocked" not in st.session_state:
    st.session_state.registration_unlocked = False
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# Login, registro ou administração
if not st.session_state.authenticated and not st.session_state.registration_mode and not st.session_state.admin_mode:
    st.subheader("Login")
    login_user = st.text_input("Usuário")
    login_pass = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (login_user, login_pass))
        user_data = c.fetchone()
        if user_data:
            st.session_state.authenticated = True
            st.session_state.username = login_user
            st.session_state.projects = user_data[3].split(",") if user_data[3] else []
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

    st.markdown("---")
    if st.button("Registrar novo usuário"):
        st.session_state.registration_mode = True
        st.rerun()
    if st.button("Painel Administrativo"):
        st.session_state.admin_mode = True
        st.rerun()

elif st.session_state.registration_mode and not st.session_state.authenticated:
    st.subheader("Registro de Novo Usuário")
    master_pass = st.text_input("Senha Mestra", type="password")
    if st.button("Liberar Acesso"):
        if master_pass == "#Heisenberg7":
            st.session_state.registration_unlocked = True
            st.success("Acesso liberado. Preencha os dados do novo usuário.")
        else:
            st.error("Senha Mestra incorreta.")

    if st.session_state.registration_unlocked:
        new_user = st.text_input("Novo Usuário")
        new_pass = st.text_input("Nova Senha", type="password")
        email = st.text_input("E-mail do usuário")
        projetos = st.text_input("Projetos permitidos (separar por vírgula)")
        if st.button("Criar usuário"):
            c.execute("SELECT * FROM users WHERE username=?", (new_user,))
            if c.fetchone():
                st.error("Usuário já existe.")
            else:
                c.execute("INSERT INTO users (username, password, email, projects) VALUES (?, ?, ?, ?)",
                          (new_user, new_pass, email, projetos))
                conn.commit()
                st.success("Usuário registrado com sucesso.")
                st.session_state.registration_mode = False
                st.session_state.registration_unlocked = False
                st.rerun()
    if st.button("Voltar ao Login"):
        st.session_state.registration_mode = False
        st.session_state.registration_unlocked = False
        st.rerun()

elif st.session_state.authenticated:
    username = st.session_state.username
    user_projects = st.session_state.projects

    st.sidebar.markdown(f"🔐 Logado como: **{username}**")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.projects = []
        st.rerun()

    st.markdown("### Upload de Arquivos")
    with st.form("upload_form"):
        project = st.selectbox("Projeto", user_projects)
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
            log_action(username, "upload", file_path)
            enviar_email_upload(username, filename, project)

    st.markdown("### Pesquisa de Documentos")
    keyword = st.text_input("Buscar por palavra-chave")
    if keyword:
        matched_files = []
        for root, _, files in os.walk(BASE_DIR):
            for file in files:
                if keyword.lower() in file.lower() and any(p in root for p in user_projects):
                    matched_files.append(os.path.join(root, file))
        if matched_files:
            st.markdown("#### Resultados da busca:")
            for file in matched_files:
                relative_path = os.path.relpath(file, BASE_DIR)
                st.write(f"📄 {relative_path}")
                with open(file, "rb") as f:
                    st.download_button(label="📥 Baixar", data=f, file_name=os.path.basename(file))
                log_action(username, "download", file)
        else:
            st.warning("Nenhum arquivo encontrado.")

    st.markdown("### Histórico de Ações")
    if st.checkbox("Mostrar log de ações"):
        logs = c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 100").fetchall()
        for log in logs:
            st.write(f"{log[0]} | Usuário: {log[1]} | Ação: {log[2]} | Arquivo: {log[3]}")
