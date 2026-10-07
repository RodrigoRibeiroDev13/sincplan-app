Analisando o código enviado, percebe-se a razão de a aplicação não pedir login para aceder às planilhas e de continuar a ler o ficheiro links.json local:

Leitura de JSON Local (links.json): O código ainda utiliza a classe LinkManager apontando para o ficheiro links.json, sem qualquer conexão ao MongoDB (pymongo).

Falta de Login Inicial: O método run() desenha imediatamente as abas ("Acessar Planilhas" e "Área Administrativa") para qualquer visitante. A senha só é pedida dentro da aba de administração, para editar os links, permitindo que a visualização das planilhas fique aberta publicamente.

Falta de Autenticação por Empresa (Multi-tenant): Não existem os perfis com senhas específicas (AVEP2026# e UNIR2026$), nem o suporte a seleção/cadastro de empresas.

Código Refatorado e Corrigido (app.py)
Abaixo está o código atualizado que integra o MongoDB Atlas (lendo a MONGO_URI das configurações/secrets) e exige o login por empresa antes de renderizar as planilhas:

Python
import os
import streamlit as st
from pymongo import MongoClient


class DatabaseManager:
    """Gerencia a persistência de dados e autenticação no MongoDB Atlas."""

    def __init__(self):
        # Obtém a URI do MongoDB a partir das variáveis do Streamlit (local ou cloud)
        mongo_uri = st.secrets.get("MONGO_URI") or os.getenv("MONGO_URI")

        if not mongo_uri:
            st.error("⚠️ Configuração do MongoDB não encontrada em secrets.toml ou variáveis de ambiente!")
            st.stop()

        self.client = MongoClient(mongo_uri)
        self.db = self.client["sincplan_db"]
        self.collection = self.db["companies"]

        # Inicializa empresas padrão se o banco estiver vazio
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Cria as empresas padrão (AVEP e UNIR) se ainda não existirem."""
        if self.collection.count_documents({}) == 0:
            default_companies = [
                {
                    "company_id": "AVEP",
                    "name": "AVEP",
                    "password": "AVEP2026#",
                    "links": {
                        "Controle de estoque operacional MG": "https://docs.google.com/spreadsheets/d/1SQIxPikyS_N0bp-Uht5Hq6mfrHqVnj158a6YFTLqVxw/edit?usp=sharing",
                        "Tabela de veículos de passeio aceitos AVEP": "https://docs.google.com/spreadsheets/d/1cuVulo4_LR6F7ALg1WzlGPmxbQWaTKE2NTmELu82X4E/edit?hl=pt-br&gid=803974951#gid=803974951",
                        "Agenda sala de reunião": "https://docs.google.com/spreadsheets/d/1oyrbtmagU6T8PfA0gUYlKRThH29baywWHuWwDKKYNvs/edit?gid=1880730452#gid=1880730452",
                    },
                },
                {
                    "company_id": "UNIR",
                    "name": "UNIR",
                    "password": "UNIR2026$",
                    "links": {},
                },
            ]
            self.collection.insert_many(default_companies)

    def get_all_companies(self) -> list:
        """Retorna a lista de todas as empresas cadastradas."""
        return list(self.collection.find({}, {"_id": 0}))

    def get_company(self, company_id: str) -> dict:
        """Busca os dados de uma empresa específica."""
        return self.collection.find_one({"company_id": company_id}, {"_id": 0})

    def authenticate(self, company_id: str, password: str) -> bool:
        """Autentica a senha de uma empresa."""
        company = self.get_company(company_id)
        if company and company.get("password") == password:
            return True
        return False

    def update_company_links(self, company_id: str, links: dict):
        """Atualiza os links das planilhas de uma empresa."""
        self.collection.update_one(
            {"company_id": company_id},
            {"$set": {"links": links}}
        )

    def save_new_company(self, name: str, password: str):
        """Cadastra uma nova empresa no MongoDB."""
        company_id = name.strip().upper().replace(" ", "_")
        self.collection.update_one(
            {"company_id": company_id},
            {
                "$set": {
                    "company_id": company_id,
                    "name": name.strip(),
                    "password": password.strip(),
                    "links": {},
                }
            },
            upsert=True,
        )


class SpreadsheetApp:
    """Controla a interface gráfica e o fluxo da aplicação Streamlit."""

    def __init__(self):
        self.db = DatabaseManager()
        self.logo_path = "logo.png"

    def run(self):
        st.set_page_config(
            page_title="Sincplan", page_icon="📊", layout="centered"
        )

        # Exibição da logomarca
        if os.path.exists(self.logo_path) or self.logo_path.startswith("http"):
            st.image(self.logo_path, width=200)

        st.title("📊 Sincplan")

        # 1. Inicializa estado da sessão
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
            st.session_state.current_company_id = None

        # 2. SE NÃO ESTIVER LOGADO -> MOSTRA TELA DE LOGIN E BLOQUEIA COM st.stop()
        if not st.session_state.logged_in:
            self.render_login_screen()
            st.stop()  # Interrompe a execução para não exibir as planilhas antes do login

        # 3. SE ESTIVER LOGADO -> MOSTRA A INTERFACE PRINCIPAL
        company_data = self.db.get_company(st.session_state.current_company_id)
        company_name = company_data.get("name", st.session_state.current_company_id)

        # Barra Lateral
        st.sidebar.markdown(f"### 🏢 Empresa Ativa:\n**{company_name}**")
        if st.sidebar.button("🚪 Sair / Logout"):
            st.session_state.logged_in = False
            st.session_state.current_company_id = None
            st.rerun()

        # Cadastro de Novas Empresas na Barra Lateral
        st.sidebar.markdown("---")
        with st.sidebar.expander("➕ Cadastrar Nova Empresa"):
            with st.form("form_add_company"):
                new_comp_name = st.text_input("Nome da Empresa:")
                new_comp_pass = st.text_input("Senha de Acesso:", type="password")
                btn_add_comp = st.form_submit_button("Cadastrar")

                if btn_add_comp:
                    if new_comp_name.strip() and new_comp_pass.strip():
                        self.db.save_new_company(new_comp_name, new_comp_pass)
                        st.success(f"Empresa '{new_comp_name}' cadastrada com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Preencha todos os campos do cadastro.")

        # Conteúdo Principal
        tab_view, tab_admin = st.tabs(
            ["📂 Acessar Planilhas", "⚙️ Gerenciar Links"]
        )

        with tab_view:
            self.render_view_tab(company_data)

        with tab_admin:
            self.render_admin_tab(company_data)

    def render_login_screen(self):
        st.subheader("🔑 Autenticação de Acesso")
        
        companies = self.db.get_all_companies()
        if not companies:
            st.error("Nenhuma empresa cadastrada no sistema.")
            return

        company_options = {c["name"]: c["company_id"] for c in companies}
        selected_name = st.selectbox("Selecione a Empresa:", list(company_options.keys()))
        password = st.text_input("Digite a Senha da Empresa:", type="password")

        if st.button("Entrar", type="primary"):
            company_id = company_options[selected_name]
            if self.db.authenticate(company_id, password):
                st.session_state.logged_in = True
                st.session_state.current_company_id = company_id
                st.success("Acesso autorizado!")
                st.rerun()
            else:
                st.error("Senha incorreta!")

    def render_view_tab(self, company_data: dict):
        st.subheader(f"Planilhas Disponíveis - {company_data.get('name')}")
        links = company_data.get("links", {})

        if not links:
            st.info("Nenhuma planilha cadastrada para esta empresa.")
            return

        for name, url in links.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{name}**")
            with col2:
                st.link_button("Abrir 🔗", url)

    def render_admin_tab(self, company_data: dict):
        company_id = company_data.get("company_id")
        links = company_data.get("links", {})

        st.subheader("➕ Adicionar Nova Planilha")
        with st.form("form_add_link", clear_on_submit=True):
            new_title = st.text_input("Nome da Planilha:")
            new_url = st.text_input("URL da Planilha:")
            add_submitted = st.form_submit_button("Adicionar Planilha")

            if add_submitted:
                if new_title.strip() and new_url.strip():
                    links[new_title.strip()] = new_url.strip()
                    self.db.update_company_links(company_id, links)
                    st.success(f"Planilha '{new_title}' adicionada com sucesso!")
                    st.rerun()
                else:
                    st.warning("Preencha o nome e a URL corretamente.")

        st.markdown("---")
        st.subheader("✏️ Editar ou Remover Planilhas")

        if not links:
            st.info("Sem planilhas para editar.")
            return

        updated_links = {}
        to_remove = []

        with st.form("form_update_links"):
            for i, (name, url) in enumerate(links.items()):
                col1, col2, col3 = st.columns([2.5, 2.5, 1])
                with col1:
                    edited_name = st.text_input(f"Nome #{i+1}", value=name, key=f"name_{i}")
                with col2:
                    edited_url = st.text_input(f"Link #{i+1}", value=url, key=f"url_{i}")
                with col3:
                    st.write("")
                    st.write("")
                    remove = st.checkbox("Remover", key=f"del_{i}")

                if remove:
                    to_remove.append(name)
                elif edited_name and edited_url:
                    updated_links[edited_name.strip()] = edited_url.strip()

            save_submitted = st.form_submit_button("Salvar Alterações")
            if save_submitted:
                for item in to_remove:
                    if item in updated_links:
                        del updated_links[item]

                self.db.update_company_links(company_id, updated_links)
                st.success("Planilhas atualizadas com sucesso!")
                st.rerun()


if __name__ == "__main__":
    app = SpreadsheetApp()
    app.run()
