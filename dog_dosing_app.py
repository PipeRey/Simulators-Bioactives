import streamlit as st
import pandas as pd
from typing import Optional

st.set_page_config(
    page_title="Siwa Bioactives Dosis Simulator",
    page_icon="🌿",
    layout="wide",
)

# ---------- Styling ----------
st.markdown("""
<style>
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #fffef2 !important; color: #262320; }
h1, h2, h3 { color: #3f4722; font-weight: 700; }
.stApp { background-color: #fffef2 !important; }
.stExpander { background-color: #ededed; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.card { background: linear-gradient(145deg, #ededed, #fffef2); padding: 15px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; transition: transform 0.2s ease, box-shadow 0.2s ease; min-height: 150px; display: flex; flex-direction: column; justify-content: space-between; }
.card:hover { transform: translateY(-5px); box-shadow: 0 6px 16px rgba(0,0,0,0.15); }
.card-title { font-size: 1.25rem; font-weight: 600; color: #3f4722; margin-bottom: 10px; }
.card-content { font-size: 1rem; color: #262320; }
.ok { color: #3f4722; font-weight: 600; }
.warn { color: #C4825A; font-weight: 600; }
.small { font-size: 0.85rem; color: #8B8B8B; }
.stButton>button { background-color: #2F3F5F; color: #fffef2; border-radius: 8px; padding: 10px 20px; font-weight: 500; transition: background-color 0.2s ease; }
.stButton>button:hover { background-color: #1E2A5C; }
.stNumberInput input, .stSelectbox, .stRadio { border-radius: 8px; border: 1px solid #3f4722; background-color: #fffef2 !important; color: #262320; outline: none !important; box-shadow: none !important; }
.stNumberInput label, .stSelectbox label, .stRadio label { color: #262320; font-weight: 500; }
.stMetric { background-color: transparent; }
.logo-container { position: absolute; top: 20px; right: 20px; z-index: 1000; }
.logo-container img { width: 120px; height: auto; }
.bottom-columns { display: flex; gap: 20px; }
@media (max-width: 768px) {
  .bottom-columns { flex-direction: column; }
  .logo-container { top: 10px; right: 10px; }
  .logo-container img { width: 100px; }
}
</style>
""", unsafe_allow_html=True)

# ---------- (Opcional) Logo ----------
# st.markdown('<div class="logo-container">', unsafe_allow_html=True)
# st.image("Siwa _ Logotipos _ Milk n Coke-3.svg", width=120)
# st.markdown('</div>', unsafe_allow_html=True)

# ---------- Standardizations for β-glucan-based method ----------
REISHI_REF_BG_PCT = 0.40   # % β-glucanos de tu reishi (editable en UI)
LION_REF_BG_PCT   = 0.25   # % β-glucanos de tu melena (editable en UI)

# ---------- PRODUCT PROFILE (mg/kg BW/day, POLVO) ----------
# Diferenciado por objetivo de marca (LM bajada a niveles similares a reishi)
PRODUCT_PROFILE = {
    "Nutriss Adultos":   {"reishi_mgkg": 12.0, "lion_mgkg":  0.0},  # +inmunidad
    "Nutriss Senior":    {"reishi_mgkg":  8.0, "lion_mgkg":  8.0},  # calma/estrés (igual a reishi)
    "Vivance Adultos":   {"reishi_mgkg": 10.0, "lion_mgkg": 10.0},  # vitalidad/enfoque (LM baja)
    "Vivance Cachorros": {"reishi_mgkg":  5.0, "lion_mgkg":  6.0},  # LM muy baja
}

# ---------- Feeding tables ----------
def load_feeding_table() -> pd.DataFrame:
    return pd.DataFrame({
        'Product': [
            'Vivance Adultos','Vivance Adultos','Vivance Adultos','Vivance Adultos','Vivance Adultos',
            'Vivance Cachorros','Vivance Cachorros','Vivance Cachorros','Vivance Cachorros','Vivance Cachorros',
            'Nutriss Adultos','Nutriss Adultos','Nutriss Adultos','Nutriss Adultos','Nutriss Adultos',
            'Nutriss Senior','Nutriss Senior','Nutriss Senior','Nutriss Senior','Nutriss Senior'
        ],
        'MinWeightKg': [1, 5, 15, 25, 50,   1, 5, 10, 15, 20,   1, 5, 14, 25, 50,   1, 5, 14, 25, 50],
        'MaxWeightKg': [5, 15, 25, 50, None, 5,10, 15, 20, 30,   5,14, 25, 50, None, 5,14, 25, 50, None],
        'FeedLowG':    [25, 75,170,250,   0, 38,95,170,230,300, 33,110,230,360,   0, 30,105,230,350,   0],
        'FeedHighG':   [75,170,250,420,   0, 95,170,230,300,350,110,230,360,600,   0,105,230,350,590,   0],
    })

def get_category(product: str) -> str:
    if 'Cachorros' in product: return 'Puppy'
    if 'Senior' in product:    return 'Senior'
    return 'Adult'

# ---------- Feeding math ----------
def _find_bin_row(product: str, weight: float, df: pd.DataFrame) -> Optional[pd.Series]:
    rows = df[df['Product'] == product].copy().sort_values(['MinWeightKg', 'MaxWeightKg'])
    for _, r in rows.iterrows():
        minw = float(r['MinWeightKg']); maxw = r['MaxWeightKg']
        if weight >= minw and (pd.isna(maxw) or weight <= float(maxw)): return r
    return None

def _interp(low_g: float, high_g: float, minw: float, maxw: float, w: float) -> float:
    if maxw <= minw: return (low_g + high_g)/2
    t = max(0.0, min(1.0, (w - minw)/(maxw - minw)))
    return low_g + (high_g - low_g)*t

def compute_feed_g_per_day(product: str, weight: float, df: pd.DataFrame) -> Optional[float]:
    row = _find_bin_row(product, weight, df)
    if row is None:
        rows = df[df['Product']==product].sort_values(['MinWeightKg','MaxWeightKg'])
        if rows.empty: return None
        if weight < float(rows.iloc[0]['MinWeightKg']):
            r = rows.iloc[0]; return (float(r['FeedLowG'])+float(r['FeedHighG']))/2
        r = rows.iloc[-1]
        if pd.isna(r['MaxWeightKg']):
            prev = rows.iloc[-2] if len(rows)>=2 else None
            base = float(prev['FeedHighG']) if prev is not None else 0.0
            extra = weight - float(r['MinWeightKg'])
            if product == 'Vivance Adultos':  return base + 6.0*extra
            if product == 'Nutriss Adultos':  return base + 8.0*extra
            if product == 'Nutriss Senior':   return base + 6.0*extra
            return base
        return float(r['FeedHighG'])
    minw = float(row['MinWeightKg']); maxw = row['MaxWeightKg']
    low_g = float(row['FeedLowG']); high_g = float(row['FeedHighG'])
    if not pd.isna(maxw): return _interp(low_g, high_g, minw, float(maxw), weight)
    rows = df[df['Product']==product].sort_values(['MinWeightKg','MaxWeightKg'])
    prev_mask = rows['MaxWeightKg'] == minw
    prev = rows[prev_mask].iloc[0] if prev_mask.any() else None
    base = float(prev['FeedHighG']) if prev is not None else 0.0
    extra = weight - minw
    if product == 'Vivance Adultos':  return base + 6.0*extra
    if product == 'Nutriss Adultos':  return base + 8.0*extra
    if product == 'Nutriss Senior':   return base + 6.0*extra
    return base

# ---------- Targets (product-based) ----------
def evidence_target_mg_per_kg_for_product(product: str) -> dict:
    p = PRODUCT_PROFILE.get(product, {"reishi_mgkg":10.0, "lion_mgkg":0.0})
    return {"reishi": p["reishi_mgkg"], "lion": p["lion_mgkg"]}

# ---------- Design weights ----------
def design_weight_by_category(category: str) -> float:
    return 6.5 if category == 'Puppy' else 15.5

# ---------- Evidence narrative ----------
def render_evidence_constant_mode(product: str,
                                  category: str,
                                  design_weight: float,
                                  design_feed_g: float,
                                  target_reishi_mgkg: float,
                                  target_lion_mgkg: float,
                                  inclusion_reishi_g_per_kg: float,
                                  inclusion_lion_g_per_kg: float,
                                  reishi_bg_pct: float,
                                  lion_bg_pct: Optional[float],
                                  lion_erinacine_mg_per_g: float,
                                  erin_from_bg_slope: float):
    st.markdown("""**Constant Inclusion Strategy**  
Fijamos una **inclusión (g/kg de alimento)** por bolsa. En un **perro de diseño** (de estudios) calibramos para alcanzar la dosis objetivo; el resto escala con alimento/peso.""")

    def block(title, target_mgkg, inclusion, bg_pct=None, erin_mg_per_g=None):
        if target_mgkg <= 0 and inclusion <= 0: return
        achieved_at_design_mgkg_powder = inclusion * design_feed_g / design_weight
        st.markdown(f"""**{title}**
- Objetivo en perro de diseño: **{target_mgkg:.0f} mg/kg/d (polvo)**
- Perro de diseño: **{design_feed_g:.0f} g/d** a **{design_weight:.1f} kg**
- Inclusión: **{inclusion:.4f} g/kg alimento**  
  → Entrega en diseño (polvo): **{achieved_at_design_mgkg_powder:.1f} mg/kg/d**""")
        if title.startswith("Reishi") and bg_pct is not None:
            bg_equiv_at_design = achieved_at_design_mgkg_powder * bg_pct
            st.markdown(f"  → β-glucanos (equivalente): **{bg_equiv_at_design:.1f} mg/kg/d**")
        if title.startswith("Melena") and erin_mg_per_g and erin_mg_per_g > 0:
            erin_at_design = (achieved_at_design_mgkg_powder/1000.0) * erin_mg_per_g  # mg/kg/d polvo → g/kg/d * mg/g
            st.markdown(f"  → Erinacinas (estimado): **{erin_at_design:.2f} mg/kg/d**")

    if target_reishi_mgkg > 0:
        block("Reishi", target_reishi_mgkg, inclusion_reishi_g_per_kg, bg_pct=reishi_bg_pct)
    if target_lion_mgkg   > 0:
        block("Melena de león", target_lion_mgkg, inclusion_lion_g_per_kg,
              bg_pct=lion_bg_pct, erin_mg_per_g=lion_erinacine_mg_per_g)

    # --- Evidence bullets (conciso, condicional) ---
    bullets = []
    if target_reishi_mgkg > 0:
        bullets.append("Perros adultos: *Ganoderma lucidum* **5–15 mg/kg/d** ~4 sem; **15 mg/kg** ↑ fagocitosis y respuesta a vacuna; bien tolerado.")
        bullets.append("β-glucanos de levadura en perros: ingestiones reales **~1.9–3.8 mg/kg/d** sin alterar digestibilidad/heces.")
    if target_lion_mgkg > 0:
        if category == "Puppy":
            bullets.append("LM en perros senior: **0.4–0.8 g/kg/d** 16 sem → microbiota beneficiosa; extrapolación prudente **6–10 mg/kg**.")
        else:
            bullets.append("LM en humanos (DCL leve): **3 g/d** (~43 mg/kg en 70 kg) 16 sem → mejora cognitiva; seguridad general aceptable.")
            bullets.append("Micelio enriquecido en **erinacina A** con potencias declaradas en ensayos clínicos; falta estandarización transversal.")
    if bullets:
        st.markdown("**Evidencia (resumen):**\n" + "\n".join([f"- {b}" for b in bullets]))

    # --- Reference list (genérico) ---
    st.markdown("**Referencias (selección):**")
    # --- Reishi & β-glucanos en perros ---
    if target_reishi_mgkg > 0:
        st.markdown("- Kayser et al., 2024. *Functional properties of Ganoderma lucidum supplementation in canine nutrition* (J. Anim. Sci.). [Resumen ASAS](https://www.asas.org/taking-stock/blog-post/taking-stock/2024/04/25/interpretive-summary-functional-properties-of-ganoderma-lucidum-supplementation-in-canine-nutrition)")
        st.markdown("- Kayser et al., 2022. *Immunological effects of Ganoderma lucidum in dogs* (abstract). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9493504/)")
        st.markdown("- Kilburn-Kappeler et al., 2023. β-glucanos de levadura en alimento para perros: procesamiento y digestibilidad. [Frontiers in Animal Science](https://www.frontiersin.org/articles/10.3389/fanim.2023.1125061/full)")
        st.markdown("- Marchi et al., 2024. *Purified β-1,3/1,6-glucans* en perros: inmunidad y microbiota. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10818568/)")
        st.markdown("- Fernandes et al., 2025. β-glucanos de levadura y digestibilidad en perros. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12416722/)")
        st.markdown("- Paris et al., 2020. β-glucanos como adyuvantes de inmunidad entrenada en caninos (rabia). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7580252/)")

    # --- Melena de león (LM), ensayos y erinacinas ---
    if target_lion_mgkg > 0:
        st.markdown("- Cho et al., 2022. *Hericium erinaceus* **0.4–0.8 g/kg/d** 16 sem en perros senior → microbiota. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9574611/)")
        st.markdown("- Mori et al., 2009. Ensayo doble ciego en DCL leve (humanos), **3 g/d** 16 semanas. [PubMed](https://pubmed.ncbi.nlm.nih.gov/18844328/)")
        st.markdown("- Li et al., 2020. Micelio enriquecido en **erinacina A**, cápsulas 350 mg (≈ **5 mg/g** EA), 49 semanas en Alzheimer leve. [Frontiers](https://www.frontiersin.org/articles/10.3389/fnagi.2020.00155/full) · [PubMed](https://pubmed.ncbi.nlm.nih.gov/32581767/)")
        st.markdown("- Docherty et al., 2023. Revisión (Nutrients) de ensayos agudos/crónicos con LM. [MDPI](https://www.mdpi.com/2072-6643/15/22/4842)")
        st.markdown("- Alzheimer’s Drug Discovery Foundation (2025). *Cognitive Vitality – Lion’s Mane* (síntesis con datos de ensayos, incluye potencia **5 mg/g EA**). [PDF](https://www.alzdiscovery.org/uploads/cognitive_vitality_media/Lions-Mane-Cognitive-Vitality-For-Researchers.pdf)")
        st.markdown("- Liu et al., 2024. Variabilidad de **erinacina A** en 17 cepas: **0.23–42.16 mg/g** (genotipo y proceso importan). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11172171/)")
        st.markdown("- Li et al., 2018. Revisión: fermentadores de 20 t reportan ≈ **5 mg/g** de erinacina A y parámetros de cultivo. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5987239/)")
        st.markdown("- Krzyczkowski et al., 2010. Biosíntesis de erinacina A en cultivo sumergido; producción y optimización. [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/elsc.201000084)")

# ---------- App ----------
def app():
    st.title("Siwa Bioactives Dosis Simulator")
    st.markdown("Diferenciación de dosis por producto y objetivo.")

    feed_df = load_feeding_table()

    with st.expander("Pet Profile & Bioactive Settings", expanded=True):
        left, right = st.columns(2, gap="medium")
        with left:
            st.subheader("Pet Details")
            product = st.selectbox('Select Product', feed_df['Product'].unique().tolist(), index=0)
            weight = st.number_input('Pet Weight (kg)', min_value=0.5, value=10.0, step=0.5)
            bag_size = st.number_input('Bag Size (kg)', min_value=1.0, value=10.0, step=0.5)
        with right:
            st.subheader("Bioactive Configuration")
            dosing_mode = st.radio("Dosing Policy", ["Evidence-Based", "Manual"], index=0)

            # Reishi: seguimos con %βG
            reishi_bg_pct = st.number_input("Reishi β-glucan (%)", min_value=1.0, max_value=80.0, value=40.0, step=1.0)/100.0

            # Lion's Mane: SIEMPRE estimamos erinacinas desde %βG con coeficiente
            lion_bg_pct = st.number_input("Lion’s Mane β-glucan (%)", min_value=1.0, max_value=80.0, value=25.0, step=1.0)/100.0
            erin_from_bg_slope = st.number_input(
                "Coeficiente (LM): mg de erinacina por cada 1% de βG (mg/g por %βG)",
                min_value=0.0, value=0.5, step=0.1,
                help="Ej.: 0.5 ⇒ 25% βG ≈ 12.5 mg/g de erinacinas. Úsalo como estimación basada en rangos de literatura."
            )
            lion_erinacine_mg_per_g = erin_from_bg_slope * (lion_bg_pct * 100.0)

            if dosing_mode == "Evidence-Based":
                method = st.radio("Method", ["Powder (study mg/kg)", "β-glucans (mg/kg)"], index=0)

    category = get_category(product)
    target = evidence_target_mg_per_kg_for_product(product)

    # Feed para perro actual
    feed_g = compute_feed_g_per_day(product, weight, feed_df)
    if feed_g is None or feed_g <= 0:
        st.warning("No feeding recommendation found for the given weight/product.")
        return

    # Inclusión (g/kg) & gramos por bolsa
    if dosing_mode == "Evidence-Based":
        design_weight = 6.5 if category == 'Puppy' else 15.5
        design_feed   = compute_feed_g_per_day(product, design_weight, feed_df)
        if design_feed is None or design_feed <= 0:
            st.warning("Design dog has no feeding recommendation; check feeding table.")
            return
        if method == "Powder (study mg/kg)":
            inclusion_reishi = (target['reishi'] * design_weight) / design_feed if target['reishi'] > 0 else 0.0
            inclusion_lion   = (target['lion']   * design_weight) / design_feed if target['lion']   > 0 else 0.0
        else:
            # βG targets at design dog (usando % de referencia para equivalencia, y re-dividiendo por % actual para manufactura)
            reishi_bg_target = target['reishi'] * REISHI_REF_BG_PCT
            lion_bg_target   = target['lion']   * LION_REF_BG_PCT
            reishi_powder_needed = (reishi_bg_target / reishi_bg_pct) if target['reishi'] > 0 else 0.0

            # LM: si no hay %βG válido, caemos al método Powder; aquí sí hay %βG
            lion_powder_needed   = (lion_bg_target   / lion_bg_pct)   if (target['lion'] > 0 and lion_bg_pct and lion_bg_pct > 0) else 0.0

            inclusion_reishi = (reishi_powder_needed * design_weight) / design_feed if reishi_powder_needed > 0 else 0.0
            inclusion_lion   = (lion_powder_needed   * design_weight) / design_feed if lion_powder_needed   > 0 else ((target['lion'] * design_weight) / design_feed if target['lion'] > 0 else 0.0)

        reishi_per_bag_g = inclusion_reishi * bag_size
        lion_per_bag_g   = inclusion_lion   * bag_size
    else:
        cols = st.columns(2)
        with cols[0]:
            reishi_per_bag_g = st.number_input("Reishi per Bag (g)", min_value=0.0, value=47.0, step=1.0)
        with cols[1]:
            lion_per_bag_g   = st.number_input("Lion’s Mane per Bag (g)", min_value=0.0, value=94.0, step=1.0)
        inclusion_reishi = reishi_per_bag_g / bag_size if bag_size > 0 else 0.0
        inclusion_lion   = lion_per_bag_g   / bag_size if bag_size > 0 else 0.0
        design_weight = None; design_feed = None

    # Entrega por día
    reishi_daily_g = inclusion_reishi * (feed_g / 1000.0)
    lion_daily_g   = inclusion_lion   * (feed_g / 1000.0)

    # βG (se mantiene para Reishi por transparencia)
    reishi_bg_mg = reishi_daily_g * 1000.0 * reishi_bg_pct

    # Erinacina (mg/d) estimada para LM desde %βG
    lion_erinacine_mg_per_day = lion_daily_g * lion_erinacine_mg_per_g if (lion_erinacine_mg_per_g and lion_erinacine_mg_per_g > 0) else 0.0

    days_supply = (bag_size * 1000.0) / feed_g

    # ---------- UI ----------
    st.header("Dosing Results")
    st.subheader("Daily Feeding & Bioactives")
    st.markdown('<div class="card"><div class="card-title">Daily Feed</div><div class="card-content">', unsafe_allow_html=True)
    st.metric("Feed Amount", f"{feed_g:.1f} g/day")
    st.markdown('</div></div>', unsafe_allow_html=True)

    cols = st.columns(2, gap="medium")
    if inclusion_reishi > 1e-9:
        with cols[0]:
            st.markdown('<div class="card"><div class="card-title">Reishi / Day</div><div class="card-content">', unsafe_allow_html=True)
            st.metric("Inclusion Rate", f"{inclusion_reishi:.4f} g/kg feed")
            st.metric("Reishi Delivered", f"{reishi_daily_g*1000:.0f} mg")
            st.metric("β-glucan Delivered", f"{reishi_bg_mg:.0f} mg")
            st.markdown('</div></div>', unsafe_allow_html=True)

    if inclusion_lion > 1e-9:
        with cols[1]:
            st.markdown('<div class="card"><div class="card-title">Lion\'s Mane / Day</div><div class="card-content">', unsafe_allow_html=True)
            st.metric("Inclusion Rate", f"{inclusion_lion:.4f} g/kg feed")
            st.metric("Lion's Mane Delivered", f"{lion_daily_g*1000:.0f} mg")
            if lion_erinacine_mg_per_day > 0:
                st.metric("Erinacine Delivered", f"{lion_erinacine_mg_per_day:.1f} mg/day")
            else:
                st.markdown('<div class="small warn">Define el coeficiente (mg/g por %βG) para estimar erinacinas desde %βG.</div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)

    st.subheader("Bag Summary")
    b1, b2, b3 = st.columns(3, gap="medium")
    b1.metric("Days of Supply", f"{days_supply:.2f} days")
    b2.metric("Reishi per Bag", f"{reishi_per_bag_g:.2f} g")
    b3.metric("Lion’s Mane per Bag", f"{lion_per_bag_g:.2f} g")

    # ---------- Ciencia & Referencias ----------
    with st.expander("Scientific Basis & References", expanded=False):
        render_evidence_constant_mode(
            product=product,
            category=category,
            design_weight=(6.5 if category == 'Puppy' else 15.5) if design_feed else 0.0,
            design_feed_g=design_feed if design_feed else 0.0,
            target_reishi_mgkg=target['reishi'],
            target_lion_mgkg=target['lion'],
            inclusion_reishi_g_per_kg=inclusion_reishi,
            inclusion_lion_g_per_kg=inclusion_lion,
            reishi_bg_pct=reishi_bg_pct,
            lion_bg_pct=lion_bg_pct,
            lion_erinacine_mg_per_g=lion_erinacine_mg_per_g,
            erin_from_bg_slope=erin_from_bg_slope
        )

if __name__ == "__main__":
    app()
