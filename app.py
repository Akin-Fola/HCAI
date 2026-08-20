"""
PMOS Symptom Pattern Explorer -- prototype artefact.

Single-script Streamlit application. Combines the tested rule-based
matching logic (from matcher_sketch.py) with a user interface, per
the architecture described in Sections 3.1.1 and 4.2.

Run locally with: streamlit run app.py
"""

import re
import streamlit as st

# --- Symptom cluster schema (identical to matcher_sketch.py) ----------

CLUSTERS = {
    "OVULATION": {
        "description": "Irregular or absent menstrual cycles",
        "phrase_terms": ["amenorrhea", "anovulation", "no period", "no periods", "missed period", "missed periods"],
        "proximity_patterns": [
            (r"period\w*", r"irregular"), (r"cycle\w*", r"irregular"),
            (r"period\w*", r"stopped"), (r"period\w*", r"infrequent"),
            (r"cycle\w*", r"infrequent"),
        ],
    },
    "METABOLIC": {
        "description": "Weight, metabolic, or glucose-related markers",
        "phrase_terms": [
            "insulin resistance", "difficulty losing weight",
            "can't lose weight", "high cholesterol", "lipid issues",
        ],
        "proximity_patterns": [
            (r"gain\w*", r"weight"), (r"gain\w*", r"pounds"),
            (r"gain\w*", r"lbs"), (r"gain\w*", r"kg"),
            (r"gain\w*", r"kilos?"), (r"gain\w*", r"stone"),
            (r"weight", r"diet"),
        ],
    },
    "ANDROGENIC": {
        "description": "Excess androgen signs or symptoms",
        "phrase_terms": [
            "hirsutism", "acne", "facial hair", "excess hair",
            "unwanted hair", "male-pattern baldness", "hair loss",
            "thinning hair",
        ],
        "proximity_patterns": [],
    },
    "PSYCHOLOGICAL": {
        "description": "Psychological or mental health impacts",
        "phrase_terms": [
            "anxiety", "anxious", "depression", "depressed",
            "mood changes", "mood swings", "stressed", "stress",
        ],
        "proximity_patterns": [],
    },
}

CONFIDENCE_THRESHOLDS = {3: "High", 2: "Moderate", 1: "Low"}
MIN_CHARS, MAX_CHARS = 50, 2000


def match_clusters(narrative: str) -> dict:
    """Match a free-text narrative against the symptom cluster schema.
    Identical logic to matcher_sketch.py -- already tested against the
    project brief's example narrative (Section 3.1.3)."""
    text = narrative.lower()
    text = re.sub(r"(\d)([a-z])", r"\1 \2", text)
    results = []

    for cluster_name, cluster_data in CLUSTERS.items():
        matched_terms = []

        for term in cluster_data["phrase_terms"]:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text):
                matched_terms.append(term)

        for word_a, word_b in cluster_data["proximity_patterns"]:
            gap = r".{0,25}"
            pattern = rf"\b{word_a}\b{gap}\b{word_b}\b|\b{word_b}\b{gap}\b{word_a}\b"
            match = re.search(pattern, text)
            if match:
                matched_terms.append(match.group(0).strip())

        if matched_terms:
            count = len(matched_terms)
            confidence = next(
                (label for threshold, label in sorted(
                    CONFIDENCE_THRESHOLDS.items(), reverse=True)
                 if count >= threshold),
                "Low",
            )
            results.append({
                "cluster_name": cluster_name,
                "description": cluster_data["description"],
                "matched_terms": matched_terms,
                "confidence": confidence,
            })

    return {"identified_clusters": results}


def build_hcp_summary(clusters: list) -> str:
    """Build a plain-language, non-diagnostic summary a user can copy or
    download to share with a healthcare professional. Distinct from the
    per-cluster reasoning display: that shows the user WHY the tool
    concluded something (FR3, explainability); this gives the user
    something actually formatted for the downstream conversation (FR8)."""
    lines = [
        "Summary to share with a healthcare professional",
        "(generated using a non-diagnostic symptom pattern tool)",
        "",
    ]
    for c in clusters:
        lines.append(f"- {c['description']}, noted from: {', '.join(c['matched_terms'])}")
    lines.append("")
    lines.append(
        "I wanted to share these patterns with you and ask whether they "
        "might be connected, and what you'd recommend as a next step."
    )
    return "\n".join(lines)


# --- Streamlit interface -----------------------------------------------
# NFR2: no narrative text is written to disk, logs, or external storage
# anywhere in this script -- it exists only in memory for this session.

st.set_page_config(page_title="Symptom Pattern Explorer", layout="centered")

st.title("Symptom pattern explorer")

# FR4 / SR1: non-diagnostic framing shown before any interaction (4.2)
st.info(
    "This tool does not diagnose PMOS. It helps you organise what you're "
    "experiencing into patterns you can discuss with a healthcare "
    "professional. It is not a substitute for clinical assessment."
)

narrative = st.text_area(
    "Describe what you've been experiencing, in your own words:",
    height=180,
    max_chars=MAX_CHARS,
    placeholder=(
        "For example: My periods have always been irregular, like every "
        "2-3 months. I've gained weight despite trying different diets..."
    ),
)

char_count = len(narrative)
st.caption(f"{char_count} / {MAX_CHARS} characters")

submitted = st.button("Find patterns")

if submitted:
    # FR1 acceptance criteria: validation message, not a silent failure
    if char_count < MIN_CHARS:
        st.error(f"Please enter at least {MIN_CHARS} characters so the "
                  f"tool has enough to work with ({char_count} entered).")
    else:
        result = match_clusters(narrative)
        clusters = result["identified_clusters"]

        st.divider()
        st.subheader("Your symptom patterns")

        if not clusters:
            # FR7: honest no-match message, not a forced low-confidence result
            st.warning(
                "No clear symptom pattern was identified from this "
                "description. This doesn't mean nothing is going on -- "
                "it may just mean this tool's current pattern list "
                "doesn't cover what you've described. A healthcare "
                "professional is still the right person to talk to."
            )
        else:
            for cluster in clusters:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{cluster['cluster_name'].title()}**")
                        st.caption(cluster["description"])
                    with col2:
                        st.markdown(f"`{cluster['confidence']} confidence`")
                    # FR3: shows the exact matched terms from the user's own input
                    st.write(
                        "Matched from what you wrote: "
                        + ", ".join(f"*{t}*" for t in cluster["matched_terms"])
                    )

            # FR8: synthesised, copyable/downloadable summary formatted for
            # the actual healthcare conversation, not just system reasoning
            st.divider()
            st.subheader("Summary to share with your healthcare professional")
            hcp_summary = build_hcp_summary(clusters)
            st.text_area(
                "You can copy this, or download it below, to bring to your appointment:",
                value=hcp_summary,
                height=180,
            )
            st.download_button(
                "Download summary",
                data=hcp_summary,
                file_name="symptom_summary.txt",
            )

        # SR2: persistent, non-dismissible disclaimer (>=14pt equivalent)
        st.markdown(
            "<div style='font-size:16px; padding:12px; border:1px solid #ccc; "
            "border-radius:6px; margin-top:16px;'>"
            "<strong>Important:</strong> This tool identifies possible symptom "
            "patterns based on what you've written. It is not a diagnosis, "
            "and it cannot replace assessment by a healthcare professional."
            "</div>",
            unsafe_allow_html=True,
        )

        # SR3: explicit recommendation to discuss with a healthcare professional
        st.success(
            "Consider bringing these patterns to your GP or another "
            "healthcare professional to discuss further."
        )
