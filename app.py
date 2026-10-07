import os
import streamlit as st
from supabase import create_client, Client


class DatabaseManager:
    """Gerencia a persistência de dados e autenticação no Supabase."""

    def __init__(self):
        url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            st.error("⚠️ Configuração SUPABASE_URL ou SUPABASE_KEY não encontrada em secrets.toml!")
            st.stop()

        try:
            self.client: Client = create_client(url, key)
            self._initialize_defaults()
        except Exception as e:
            st.error(f"❌ Erro ao conectar ao Supabase: {e}")
            st.stop()

    def _initialize_defaults(self):
        """Insere as empresas padrão se a tabela estiver vazia."""
        res = self.client.table("companies").select("id", count="exact").execute()
        if res.count == 0:
            default_companies = [
                {
                    "company_id": "AVEP",
                    "name": "AVEP",
                    "password": "AVEP2026Password",
                    "links": {
                        "Controle de estoque operacional MG": "https://docs.google.com/spreadsheets/d/1SQIxPikyS_N0bp-Uht5Hq6mfrHqVnj158a6YFTLqVxw/edit?usp=sharing",
                        "Tabela de veículos de passeio aceitos AVEP": "https://docs.google.com/spreadsheets/d/1cuVulo4_LR6F7ALg1WzlGPmxbQWaTKE2NTmELu82X4E/edit?hl=pt-br&gid=803974951#gid=803974951",
                        "Agenda sala de reunião": "https://docs.google.com/spreadsheets/d/1oyrbtmagU6T8PfA0gUYlKRThH29baywWHuWwDKKYNvs/edit?gid=1880730452#gid=1880730452",
                    },
                },
                {
                    "company_id": "UNIR",
                    "name": "UNIR",
                    "password": "UNIR2026Password",
                    "links": {},
                },
            ]
            self.client.table("companies").insert(default_companies).execute()

    def get_all_companies(self) -> list:
        res = self.client.table("companies").select("company_id, name").execute()
        return res.data or []

    def get_company(self, company_id: str) -> dict:
        res = self.client.table("companies").select("*").eq("company_id", company_id).execute()
        return res.data[0] if res.data else {}

    def authenticate(self, company_id: str, password: str) -> bool:
        company = self.get_company(company_id)
        return company.get("password") == password if company else False

    def update_company_links(self, company_id: str, links: dict):
        self.client.table("companies").update({"links": links}).eq("company_id", company_id).execute()

    def save_new_company(self, name: str, password: str):
        company_id = name.strip().upper().replace(" ", "_")
        payload = {
            "company_id": company_id,
            "name": name.strip(),
            "password": password.strip(),
            "links": {},
        }
        self.client.table("companies").upsert(payload, on_conflict="company_id").execute()


class SpreadsheetApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.logo_path = "logo.png"

    def run(self):
        st.set_page_config(page_title="Sincplan", page_icon="📊", layout="centered")

        if os.path.exists(self.logo_path) or self.logo_path.startswith("http"):
            st.image(self.logo_path, width=200)

        st.title("📊 Sincplan")

        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
            st.session_state.current_company_id = None

        if not st.session_state.logged_in:
            self.render_login_screen()
            st.stop()

        company_data = self.db.get_company(st.session_state.current_company_id)
        company_name = company_data.get("name", st.session_state.current_company_id)

        st.sidebar.markdown(f"### 🏢 Empresa Ativa:\n**{company_name}**")
        if st.sidebar.button("🚪 Sair / Logout"):
            st.session_state.logged_in = False
            st.session_state.current_company_id = None
            st.rerun()

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

        tab_view, tab_admin = st.tabs(["📂 Acessar Planilhas", "⚙️ Gerenciar Links"])

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
