import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="Readiness Radar – Defesa",
    layout="wide",
)

st.title("Readiness Radar – Prontidão para a Defesa")
st.markdown(
    """
Avalie a sua empresa em cinco dimensões chave e visualize o nível de prontidão num gráfico em forma de radar.

Escala usada em todas as perguntas:

- 1 – Muito fraco / inexistente  
- 2 – Fraco  
- 3 – Moderado  
- 4 – Bom  
- 5 – Muito desenvolvido / pronto para Defesa
"""
)

# -------------------------
# Dimensões e perguntas
# -------------------------
dimensions = {
    "Produto": [
        "O produto/serviço tem, pelo menos, um protótipo funcional testado em ambiente relevante (piloto, laboratório, utilizadores)?",
        "O produto responde claramente a necessidades da área de Defesa (vigilância, logística, ciber, comando e controlo, etc.)?",
        "Já identificámos requisitos técnicos específicos de Defesa (normas, standards, interoperabilidade) e começámos a adequar o produto?",
        "Temos capacidade de produção/entrega (interna ou em parceria) para pilotos ou pequenos contratos em Defesa?",
    ],
    "Mercado": [
        "Conhecemos bem os principais clientes e decisores na área de Defesa (Ministério, Forças Armadas, NATO, UE, integradores)?",
        "Já tivemos reuniões ou contactos ativos com potenciais clientes ou parceiros na área de Defesa?",
        "Temos parcerias estratégicas com empresas/entidades já estabelecidas no setor de Defesa?",
        "Temos uma proposta de valor específica para Defesa, distinta da oferta 'civil' que já fazemos?",
    ],
    "Documentação": [
        "A propriedade intelectual relevante (patentes, software, marcas) está identificada e protegida quando necessário?",
        "A documentação técnica (arquiteturas, especificações, manuais, fichas técnicas) está organizada e atualizada?",
        "Temos minutas de NDA e contratos-tipo adequadas para pilotos e parcerias em contexto de Defesa?",
        "Já identificámos e iniciámos processos de credenciação/licenciamento relevantes para atuar em Defesa?",
    ],
    "Segurança": [
        "Temos políticas mínimas de segurança da informação (controlo de acessos, passwords, backups, gestão de dispositivos)?",
        "A informação sensível (código, dados, documentação crítica) está protegida (encriptação, acessos restritos, separação de ambientes)?",
        "A equipa-chave recebeu alguma formação/sensibilização em cibersegurança e proteção de informação?",
        "As instalações/processos têm medidas de segurança física e organizacional adequadas (acesso controlado, registo de visitas, zonas restritas)?",
    ],
    "Certificações": [
        "Temos certificações de qualidade relevantes (ex.: ISO 9001) ou processos internos já próximos desse nível?",
        "Temos ou estamos a implementar práticas/certificações de segurança da informação (ex.: ISO 27001)?",
        "Já identificámos normas/certificações específicas para a Defesa ou setores afins (aeronáutica, espacial, ciber) que possam ser exigidas?",
        "Existe um roadmap de certificações com prioridades, prazos e recursos estimados?",
    ],
}


def interpret_score(score: float) -> str:
    if score <= 1.5:
        return "Crítico"
    if score <= 2.5:
        return "Fraco"
    if score <= 3.5:
        return "Moderado"
    if score <= 4.5:
        return "Bom"
    return "Muito bom"


# -------------------------
# Layout em colunas
# -------------------------
col_form, col_radar = st.columns([2.2, 1.8])

answers = {}
dimension_scores = {}

with col_form:
    st.subheader("Questionário de Prontidão")

    for dim_name, questions in dimensions.items():
        with st.expander(dim_name, expanded=True):
            total = 0
            for i, q in enumerate(questions, start=1):
                key = f"{dim_name}_{i}"
                value = st.slider(
                    q,
                    min_value=1,
                    max_value=5,
                    value=3,
                    step=1,
                    key=key,
                    help="1 = Muito fraco · 5 = Muito desenvolvido",
                )
                answers[key] = value
                total += value

            avg = round(total / len(questions), 2)
            dimension_scores[dim_name] = avg
            st.markdown(
                f"**Score médio em _{dim_name}_:** {avg} · {interpret_score(avg)}"
            )

with col_radar:
    st.subheader("Radar de Prontidão")

    labels = list(dimensions.keys())
    values = [dimension_scores[d] for d in labels]

    # fechar polígono
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            name="Prontidão",
            line=dict(color="seagreen"),
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickvals=[0, 1, 2, 3, 4, 5],
            )
        ),
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Interpretação rápida")
    for dim, score in dimension_scores.items():
        st.markdown(f"- **{dim}**: {score} · {interpret_score(score)}")

overall = round(sum(dimension_scores.values()) / len(dimension_scores), 2)
st.markdown("---")
st.markdown(
    f"**Score global de prontidão:** {overall} · {interpret_score(overall)}"
)


