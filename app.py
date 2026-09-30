"""
app.py - BridgeSnap: VLM-Based Preliminary Bridge Damage Assessment Chatbot.
A Streamlit web application powered by Google Gemini Vision-Language Models.
Designed for preliminary bridge visual inspection, damage classification, and multi-turn condition analysis.
"""

import os
import streamlit as st
from google import genai
from google.genai import types

from prompts import (
    SYSTEM_PROMPT,
    WELCOME_MESSAGE_TEMPLATE,
    DEFAULT_IMAGE_ANALYSIS_PROMPT,
    SUMMARY_REQUEST_PROMPT,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="BridgeSnap — VLM Bridge Damage Assessment",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Subtle styling enhancements for clean academic / engineering presentation
st.markdown(
    """
    <style>
    .report-card {
        background-color: #f8f9fa;
        border-left: 5px solid #0d6efd;
        padding: 1.2rem;
        border-radius: 6px;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .disclaimer-badge {
        font-size: 0.85rem;
        color: #6c757d;
        border: 1px dashed #ced4da;
        padding: 0.5rem 0.8rem;
        border-radius: 4px;
        background-color: #fff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 2. API Key & Model Configuration
# -----------------------------------------------------------------------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
CONFIGURED_MODEL = st.secrets.get("MODEL_NAME", os.environ.get("MODEL_NAME", "gemini-3.5-flash"))

# Sidebar for project context, model selector, and optional API key fallback
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1545558014-8692077e9b5c?w=600&auto=format&fit=crop&q=80",
        caption="Civil Infrastructure Condition Analysis",
    )
    st.subheader("Major Project Metadata")
    st.markdown(
        """
        **System:** BridgeSnap Prototype  
        **Paradigm:** Vision-Language Model (VLM)  
        **Target Domain:** Preliminary Bridge Condition Assessment  
        **Key Components:**
        - Cracking & Fissures
        - Spalling & Delamination
        - Corrosion & Rust Stains
        - Exposed Reinforcement
        - Concrete Surface Scaling
        """
    )

    st.divider()

    # Model selector with tested low-traffic models
    SUPPORTED_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.1-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
    ]
    default_idx = (
        SUPPORTED_MODELS.index(CONFIGURED_MODEL)
        if CONFIGURED_MODEL in SUPPORTED_MODELS
        else 0
    )
    selected_model = st.selectbox(
        "Vision-Language Model",
        SUPPORTED_MODELS,
        index=default_idx,
        help="Select the Gemini VLM model. 'gemini-3-flash-preview' and 'gemini-3.1-flash-lite-preview' have zero traffic congestion.",
    )
    MODEL_NAME = selected_model

    # Allow setting or overriding key in UI if secrets.toml is not yet created
    if not GEMINI_API_KEY:
        st.warning("⚠️ No Gemini API Key detected in `.streamlit/secrets.toml`.")
        user_key = st.text_input(
            "Enter Gemini API Key for this session:",
            type="password",
            placeholder="AIzaSy...",
            help="Get your free key at https://aistudio.google.com/",
        )
        if user_key.strip():
            GEMINI_API_KEY = user_key.strip()
            st.success("API key stored for session.")

    st.caption(f"Active VLM: `{MODEL_NAME}`")
    st.markdown(
        """
        <div class="disclaimer-badge">
        ⚠️ <b>Academic Notice:</b> This tool provides preliminary 2D visual analysis. It does NOT substitute for hands-on, non-destructive testing (NDT) or professional structural engineering inspection.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Stop execution if API key is completely missing
if not GEMINI_API_KEY:
    st.title("🏗️ BridgeSnap")
    st.info(
        """
        ### Welcome to BridgeSnap
        Please configure your **Gemini API Key** to begin:
        1. Create a `.streamlit/secrets.toml` file based on `.streamlit/secrets.toml.example`.
        2. Or enter your key temporarily in the left sidebar.
        """
    )
    st.stop()


# -----------------------------------------------------------------------------
# 3. Cached VLM Client
# -----------------------------------------------------------------------------
@st.cache_resource
def get_gemini_client(api_key: str):
    """
    Initializes and caches the Google GenAI Client.
    Streamlit re-executes scripts on every user interaction; wrapping client
    instantiation in @st.cache_resource prevents rebuilding the client repeatedly.
    """
    return genai.Client(api_key=api_key)


gemini_client = get_gemini_client(GEMINI_API_KEY)


# -----------------------------------------------------------------------------
# 4. Message Rendering Helpers
# -----------------------------------------------------------------------------
def render_message(message: dict):
    """Renders a single chat history item (text or image) in the chat timeline."""
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.markdown(message["content"])
        elif message["kind"] == "image":
            caption = message.get("caption", "Uploaded Bridge Image")
            st.image(message["content"], caption=caption)


def add_message(role: str, kind: str, content, caption: str = None):
    """Appends a message to session state and renders it immediately."""
    msg = {"role": role, "kind": kind, "content": content}
    if caption:
        msg["caption"] = caption
    st.session_state.messages.append(msg)
    render_message(msg)


def optimize_image(image_bytes: bytes, max_dim: int = 1280, quality: int = 85) -> tuple[bytes, str]:
    """
    Compresses and downscales large camera images in memory before upload.
    Reduces multi-megabyte uploads to ~150KB, drastically cutting network latency
    and VLM tokenization time without loss of crack/spall visual fidelity.
    """
    from PIL import Image
    import io
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        out_buf = io.BytesIO()
        img.save(out_buf, format="JPEG", quality=quality, optimize=True)
        return out_buf.getvalue(), "image/jpeg"
    except Exception:
        return image_bytes, "image/jpeg"


def stream_gemini(parts: list):
    """
    Streams response tokens in real-time as they are generated by the VLM.
    Users see words appear in < 1 second instead of waiting 10-15 seconds for a full batch.
    Includes seamless multi-model fallback on 503/429 errors.
    """
    try:
        response_stream = st.session_state.chat.send_message_stream(parts)
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    except Exception as first_error:
        first_err_str = str(first_error)
        if "503" in first_err_str or "high demand" in first_err_str.lower() or "429" in first_err_str:
            fallback_models = [m for m in SUPPORTED_MODELS if m != st.session_state.get("current_model")]
            for fallback in fallback_models:
                try:
                    new_chat = gemini_client.chats.create(
                        model=fallback,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.2,
                        ),
                    )
                    stream = new_chat.send_message_stream(parts)
                    for chunk in stream:
                        if chunk.text:
                            yield chunk.text
                    st.session_state.chat = new_chat
                    st.session_state.current_model = fallback
                    return
                except Exception:
                    continue
        yield f"⚠️ **Error communicating with VLM:** {first_err_str}"


def ask_gemini(parts: list) -> str:
    """Batch generation used for assessment summary."""
    try:
        response = st.session_state.chat.send_message(parts)
        return response.text
    except Exception as first_error:
        first_err_str = str(first_error)
        if "503" in first_err_str or "high demand" in first_err_str.lower() or "429" in first_err_str:
            fallback_models = [m for m in SUPPORTED_MODELS if m != st.session_state.get("current_model")]
            for fallback in fallback_models:
                try:
                    new_chat = gemini_client.chats.create(
                        model=fallback,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.2,
                        ),
                    )
                    response = new_chat.send_message(parts)
                    st.session_state.chat = new_chat
                    st.session_state.current_model = fallback
                    return response.text
                except Exception:
                    continue

        return f"⚠️ **Error communicating with VLM:** {first_err_str}"


# -----------------------------------------------------------------------------
# 5. Onboarding Screen
# -----------------------------------------------------------------------------
if "onboarded" not in st.session_state:
    st.title("🏗️ BridgeSnap — Setup Inspection Session")
    st.caption("VLM-Based Preliminary Bridge Damage Assessment and Condition Analysis")

    st.markdown(
        """
        Welcome to the **BridgeSnap** research prototype.  
        Before initializing the Vision-Language Model conversational session, please enter your details.
        """
    )

    with st.form("onboarding_form"):
        name = st.text_input(
            "Inspector / Student Name",
            placeholder="e.g., Sarah Chen or Structural Research Team",
            help="Used to personalize the session and assessment reports.",
        )
        inspection_focus = st.selectbox(
            "Primary Inspection Focus (Optional)",
            [
                "General Bridge Visual Screening",
                "Concrete Cracking & Fissure Analysis",
                "Spalling & Delamination",
                "Steel & Rebar Corrosion",
                "Substructure / Pier Assessment",
                "Superstructure / Girder & Deck Assessment",
            ],
        )

        submitted = st.form_submit_button("Start Assessment Session 🚀")

        if submitted:
            if not name.strip():
                st.warning("Please provide a name or identifier to start the session.")
            else:
                st.session_state.name = name.strip()
                st.session_state.inspection_focus = inspection_focus
                st.session_state.assessment_summary = None

                # Initialize stateful Gemini chat session with system instruction
                try:
                    st.session_state.chat = gemini_client.chats.create(
                        model=MODEL_NAME,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.2,  # Low temperature for objective engineering consistency
                        ),
                    )
                except Exception as err:
                    st.error(f"Failed to initialize VLM chat session: {err}")
                    st.stop()

                st.session_state.current_model = MODEL_NAME
                st.session_state.messages = []
                st.session_state.onboarded = True
                st.rerun()

    st.stop()


# -----------------------------------------------------------------------------
# 6. Main Chat & Inspection Interface
# -----------------------------------------------------------------------------
# Ensure chat instance matches selected sidebar model
if "current_model" not in st.session_state or st.session_state.current_model != MODEL_NAME:
    st.session_state.current_model = MODEL_NAME
    st.session_state.chat = gemini_client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )

# Top Bar: Header and Assessment Summary Trigger
header_col, action_col = st.columns([5, 2], vertical_alignment="center")

with header_col:
    st.title("🏗️ BridgeSnap")
    st.caption(
        f"**Inspector:** {st.session_state.name} | "
        f"**Focus:** {st.session_state.get('inspection_focus', 'General')} | "
        f"**Mode:** Preliminary VLM Visual Screening"
    )

with action_col:
    # Summary button is disabled until at least one substantive user-assistant interaction exists
    has_observations = len(st.session_state.messages) > 1
    if st.button("📋 Generate Assessment Summary", disabled=not has_observations, use_container_width=True):
        with st.spinner("Compiling structured bridge condition summary..."):
            summary_result = ask_gemini([SUMMARY_REQUEST_PROMPT])
            st.session_state.assessment_summary = summary_result

    if st.button("🔄 Reset Inspection", use_container_width=True):
        # Clear state to restart session
        for key in ["onboarded", "name", "chat", "messages", "assessment_summary", "inspection_focus"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Display Assessment Summary Card if generated
if st.session_state.get("assessment_summary"):
    with st.expander("📑 Formal Preliminary Assessment Report (Click to collapse)", expanded=True):
        st.markdown(st.session_state.assessment_summary)
        st.download_button(
            label="💾 Download Assessment Report (.md)",
            data=st.session_state.assessment_summary,
            file_name=f"BridgeSnap_Report_{st.session_state.name.replace(' ', '_')}.md",
            mime="text/markdown",
        )

st.divider()

# Replay conversation history
if not st.session_state.messages:
    welcome_text = WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name)
    add_message("assistant", "text", welcome_text)
else:
    for message in st.session_state.messages:
        render_message(message)

# -----------------------------------------------------------------------------
# 7. User Input: Multimodal Chat (Text + Image Upload)
# -----------------------------------------------------------------------------
user_input = st.chat_input(
    "Ask a question or upload a bridge / component photograph...",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text_content = user_input.text.strip() if user_input.text else ""
    query_parts = []

    # Handle image attachment with ultra-fast optimization
    if photo is not None:
        photo_bytes = photo.getvalue()
        # Compress and downscale large photos in memory to accelerate upload and inference
        opt_bytes, opt_mime = optimize_image(photo_bytes)
        # Render and record image in chat timeline
        add_message("user", "image", opt_bytes, caption=f"Bridge Image: {photo.name}")
        query_parts.append(types.Part.from_bytes(data=opt_bytes, mime_type=opt_mime))

    # Handle accompanying or standalone text
    if text_content:
        add_message("user", "text", text_content)
        query_parts.append(text_content)
    elif photo is not None:
        # User uploaded photo without specific text; supply domain assessment prompt
        query_parts.append(DEFAULT_IMAGE_ANALYSIS_PROMPT)

    # Execute real-time streaming VLM inference (renders immediately token-by-token)
    if query_parts:
        with st.chat_message("assistant"):
            response_text = st.write_stream(stream_gemini(query_parts))
        st.session_state.messages.append({"role": "assistant", "kind": "text", "content": response_text})
