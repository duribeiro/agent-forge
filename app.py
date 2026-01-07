
import streamlit as st
import os
import io
import zipfile
from backend import generate_agent_assets, check_api_key, get_chat_response

st.set_page_config(page_title="Agent Forge", page_icon="🤖", layout="wide")

# Initialize Session State
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = None
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("🤖 Agent Forge (Fábrica de Agentes)")
st.markdown("Transforme vídeos brutos em **Agentes de IA Especializados** em minutos.")

# Check API Key
if not check_api_key():
    st.error("⚠️ API Key não encontrada! Verifique o arquivo .env.")
    st.stop()

# Layout
col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Ingestão")
    uploaded_file = st.file_uploader("Upload de Vídeo (.mp4)", type=["mp4"])
    
    agent_goal = st.text_area(
        "Objetivo do Agente",
        placeholder="Ex: Agente de Suporte Técnico que responde dúvidas sobre o vídeo com tom amigável.",
        height=150
    )
    
    if st.button("🔨 Forjar Agente", type="primary"):
        if uploaded_file and agent_goal:
            # Save temp file
            temp_path = os.path.join("temp_video.mp4")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.info("🚀 Enviando para a Forja (Gemini Flash)... Isso pode levar 1-2 minutos.")
            
            try:
                # Call Backend
                with st.spinner("Extraindo Conhecimento & Engenharia de Persona..."):
                    kb, sys_prompt = generate_agent_assets(temp_path, agent_goal)
                
                # Save to Session State (Persist!)
                st.session_state.knowledge_base = kb
                st.session_state.system_prompt = sys_prompt
                st.session_state.chat_history = [] # Reset chat on new forge
                
                st.success("✅ Agente Forjado com Sucesso!")
                
            except Exception as e:
                st.error(f"Falha na Forja: {e}")
        else:
            st.warning("⚠️ Faça upload do vídeo e defina o objetivo!")

with col2:
    st.header("2. Resultado (O Cérebro)")
    
    if st.session_state.knowledge_base and st.session_state.system_prompt:
        
        # Zip Logic
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("knowledge_base.md", st.session_state.knowledge_base)
            zf.writestr("system_prompt.txt", st.session_state.system_prompt)
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "📦 Baixar Pacote Completo (.zip)",
                data=zip_buffer.getvalue(),
                file_name="agent_pack.zip",
                mime="application/zip",
                use_container_width=True
            )
        
        tab1, tab2, tab3 = st.tabs(["💬 Testar Agente", "🧠 Base de Conhecimento", "🎭 System Prompt"])
        
        with tab1:
            st.subheader("Sala de Teste (Preview)")
            st.caption("Converse com o agente que você acabou de criar.")
            
            # Display Chat History
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Chat Input
            if prompt := st.chat_input("Diga oi para seu agente..."):
                # User Message
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # AI Response
                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        response = get_chat_response(
                            st.session_state.chat_history, 
                            st.session_state.system_prompt,
                            st.session_state.knowledge_base
                        )
                        st.markdown(response)
                
                st.session_state.chat_history.append({"role": "assistant", "content": response})

        with tab2:
            st.subheader("Conhecimento Higienizado")
            st.text_area("Markdown", st.session_state.knowledge_base, height=400)
            st.download_button("Download KB (.md)", st.session_state.knowledge_base, "knowledge_base.md")
            
        with tab3:
            st.subheader("Instrução de Sistema (Prompt)")
            st.text_area("Prompt", st.session_state.system_prompt, height=400)
            st.download_button("Download Prompt (.txt)", st.session_state.system_prompt, "system_prompt.txt")
            
    else:
        st.info("👈 Faça o upload e clique em 'Forjar Agente' para ver o resultado.")

st.markdown("---")
st.caption("Powered by Gemini 1.5 Flash • Agent Forge v0.2 Beta")
