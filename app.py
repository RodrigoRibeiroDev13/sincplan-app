import json
import os
import streamlit as st


class LinkManager:
    """Gerencia o armazenamento, leitura e atualização dos links das planilhas."""

    def __init__(self, storage_file="links.json"):
        self.storage_file = storage_file
        self.default_links = {
            "Controle de estoque operacional MG": "https://docs.google.com/spreadsheets/d/1SQIxPikyS_N0bp-Uht5Hq6mfrHqVnj158a6YFTLqVxw/edit?usp=sharing",
            "Tabela de veículos de passeio aceitos AVEP": "https://docs.google.com/spreadsheets/d/1cuVulo4_LR6F7ALg1WzlGPmxbQWaTKE2NTmELu82X4E/edit?hl=pt-br&gid=803974951#gid=803974951",
            "Agenda sala de reunião": "https://docs.google.com/spreadsheets/d/1oyrbtmagU6T8PfA0gUYlKRThH29baywWHuWwDKKYNvs/edit?gid=1880730452#gid=1880730452",
        }

    def load_links(self) -> dict:
        """Carrega os links do ficheiro JSON ou cria o ficheiro inicial se não existir."""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return self.default_links
        else:
            self.save_links(self.default_links)
            return self.default_links

    def save_links(self, links: dict):
        """Guarda o dicionário de links no ficheiro JSON."""
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump(links, f, ensure_ascii=False, indent=4)


class SpreadsheetApp:
    """Controla a interface gráfica e o fluxo da aplicação Streamlit."""

    def __init__(self):
        self.link_manager = LinkManager()
        self.admin_password = "senha123"  # Senha padrão de exemplo
        self.logo_path = "logo.png"       # Nome do ficheiro da logomarca ou URL

    def run(self):
        st.set_page_config(
            page_title="Sincplan", page_icon="📊", layout="centered"
        )

        # --- EXIBIÇÃO DA LOGOMARCA ---
        # Caso tenha um ficheiro local 'logo.png' ou use uma URL
        if os.path.exists(self.logo_path) or self.logo_path.startswith("http"):
            st.image(self.logo_path, width=200)

        st.title("📊 Sincplan")
        st.write(
            "Selecione uma planilha para abrir ou acesse a aba administrativa"
            " para gerenciar os links."
        )

        tab_view, tab_admin = st.tabs(
            ["📂 Acessar Planilhas", "⚙️ Área Administrativa"]
        )

        with tab_view:
            self.render_view_tab()

        with tab_admin:
            self.render_admin_tab()

    def render_view_tab(self):
        st.subheader("Planilhas Disponíveis")
        links = self.link_manager.load_links()

        if not links:
            st.info("Nenhuma planilha cadastrada.")
            return

        for name, url in links.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{name}**")
            with col2:
                st.link_button("Abrir 🔗", url)

    def render_admin_tab(self):
        st.subheader("Gerenciar Links de Planilhas")
        password = st.text_input("Digite a senha de acesso:", type="password")

        if password == self.admin_password:
            st.success("Acesso autorizado!")
            links = self.link_manager.load_links()

            # --- SECÇÃO 1: ADICIONAR NOVA PLANILHA ---
            st.markdown("---")
            st.subheader("➕ Adicionar Nova Planilha")
            with st.form("form_add_link", clear_on_submit=True):
                new_title = st.text_input("Nome da Planilha:")
                new_url = st.text_input("URL da Planilha:")
                add_submitted = st.form_submit_button("Adicionar Planilha")

                if add_submitted:
                    if new_title.strip() and new_url.strip():
                        links[new_title.strip()] = new_url.strip()
                        self.link_manager.save_links(links)
                        st.success(f"Planilha '{new_title}' adicionada com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Preencha o nome e o link corretamente.")

            # --- SECÇÃO 2: EDITAR / REMOVER PLANILHAS EXISTENTES ---
            st.markdown("---")
            st.subheader("✏️ Editar ou Remover Planilhas")

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
                        st.write("")  # Espaçamento para alinhar a checkbox
                        st.write("")
                        remove = st.checkbox("Remover", key=f"del_{i}")

                    if remove:
                        to_remove.append(name)
                    elif edited_name and edited_url:
                        updated_links[edited_name.strip()] = edited_url.strip()

                save_submitted = st.form_submit_button("Salvar Alterações")
                if save_submitted:
                    # Remove os itens selecionados para exclusão
                    for item in to_remove:
                        if item in updated_links:
                            del updated_links[item]

                    self.link_manager.save_links(updated_links)
                    st.success("Planilhas atualizadas com sucesso!")
                    st.rerun()

        elif password:
            st.error("Senha incorreta.")


if __name__ == "__main__":
    app = SpreadsheetApp()
    app.run()