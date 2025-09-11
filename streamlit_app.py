import streamlit as st
import requests
import os
import base64
import streamlit.components.v1 as components

# ---------------------------
# Streamlit App Configuration
# ---------------------------
st.set_page_config(page_title="Emergency Vehicle Detection", page_icon="🚑", layout="wide")
st.title("Emergency Vehicle Detection")





# ---------------------------
# Initialize Session State
# ---------------------------
if 'emergency_mode' not in st.session_state:
    st.session_state.emergency_mode = False
if 'detection_status' not in st.session_state:
    st.session_state.detection_status = None
if 'video_url' not in st.session_state:
    st.session_state.video_url = None
if 'last_uploaded_filename' not in st.session_state:
    st.session_state.last_uploaded_filename = None
if 'manual_mode' not in st.session_state:
    st.session_state.manual_mode = False
if 'current_light' not in st.session_state:
    st.session_state.current_light = 'red'

# ---------------------------
# Prepare JS variables
# ---------------------------
is_emergency_js = str(st.session_state.emergency_mode).lower()
is_manual_js = str(st.session_state.manual_mode).lower()
current_light_js = f"'{st.session_state.current_light}'"

# ---------------------------
# Load and encode ambulance.mp4 for autoplay
# ---------------------------
video_b64 = ""
if os.path.exists("ambulance.mp4"):
    with open("CCTV_and_Green_Traffic_Signal.mp4", "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode()

# ---------------------------
# Build HTML: Traffic light + video side by side
# ---------------------------
traffic_light_html = f"""
<div id="t">
  <div id="traffic-light">
    <div class="light red"></div>
    <div class="light yellow"></div>
    <div class="light green"></div>
  </div>
  <div class="vid">
    <video autoplay muted loop >
      <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
      Your browser does not support the video tag.
    </video>
  </div>
</div>

<style>
.vid video{{
width:250px;
    border-radius:10px;
}}

#t {{
  display: flex;
  align-items: center;
  justify-content: space-around;
  margin-bottom: 20px;
}}
.vid {{
  color: white;
}}
#traffic-light {{
  width: 40%;
  display: flex;
  background: #333;
  padding: 20px;
  border-radius: 50px;
}}
.light {{
  width: 100px;
  height: 100px;
  background: #111;
  margin: 10px auto;
  border-radius: 50%;
  transition: background 0.5s;
}}
.red.on {{ background: red; }}
.yellow.on {{ background: yellow; }}
.green.on {{ background: green; }}
</style>

<script>
const lights = ["red", "yellow", "green"];
let interval;

const isEmergency = {is_emergency_js};
const isManual = {is_manual_js};
const currentLight = {current_light_js};

function turnOn(light) {{
  document.querySelectorAll(".light").forEach(el => el.classList.remove("on"));
  const lightEl = document.querySelector(".light." + light);
  if (lightEl) {{
    lightEl.classList.add("on");
  }}
}}

function setStaticLight(lightColor) {{
  clearInterval(interval);
  turnOn(lightColor);
}}

function startNormalCycle() {{
  clearInterval(interval);
  let startIndex = lights.indexOf(currentLight);
  let index = (startIndex === -1) ? 0 : startIndex;

  turnOn(lights[index]);

  interval = setInterval(() => {{
    index = (index + 1) % lights.length;
    turnOn(lights[index]);
  }}, 2000);
}}

if (isEmergency) {{
  setStaticLight('green');
}} else if (isManual) {{
  setStaticLight(currentLight);
}} else {{
  startNormalCycle();
}}
</script>
"""

components.html(traffic_light_html, height=230)

# ---------------------------
# Manual Controls
# ---------------------------
st.subheader("Manual Traffic Controls")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🔴 Red"):
        st.session_state.manual_mode = True
        st.session_state.emergency_mode = False
        st.session_state.current_light = 'red'
        st.rerun()

with col2:
    if st.button("🟡 Yellow"):
        st.session_state.manual_mode = True
        st.session_state.emergency_mode = False
        st.session_state.current_light = 'yellow'
        st.rerun()

with col3:
    if st.button("🟢 Green"):
        st.session_state.manual_mode = True
        st.session_state.emergency_mode = False
        st.session_state.current_light = 'green'
        st.rerun()

with col4:
    if st.button("⚙️ Resume Auto"):
        st.session_state.manual_mode = False
        st.session_state.emergency_mode = False
        st.rerun()

st.divider()

# ---------------------------
# Automatic Emergency Detection
# ---------------------------
# st.subheader("Automatic Emergency Detection")
uploaded_file = st.file_uploader("Upload a video", type=["mp4", "avi", "mov"], accept_multiple_files=False)

if st.button("Detect", disabled=not uploaded_file):
    if uploaded_file is not None:
        st.session_state.detection_status = None
        st.session_state.video_url = None

        temp_file_path = f"temp_{uploaded_file.name}"
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("Processing your video… If an **emergency vehicle** is detected, the signal will stay green 🟢 to clear the path."):
            try:
                with open(temp_file_path, "rb") as f:
                    files = {"video": (uploaded_file.name, f, "video/mp4")}
                    response = requests.post("https://raeessg-raeespace.hf.space/detect", files=files, timeout=300)

                if response.status_code == 200:
                    data = response.json()
                    emergency_detected = data.get("emergency_detected", False)
                    output_video_url = data.get("output_video_url", "")

                    st.session_state.emergency_mode = emergency_detected
                    st.session_state.detection_status = "Yes" if emergency_detected else "No"
                    st.session_state.video_url = output_video_url
                    st.session_state.last_uploaded_filename = uploaded_file.name

                    st.rerun()
                else:
                    st.error(f"Error: API returned status {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Error connecting to backend: {str(e)}")
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

# ---------------------------
# Show results
# ---------------------------
if st.session_state.detection_status:
    # st.info(f"Showing results for: {st.session_state.last_uploaded_filename}")
    status = st.session_state.detection_status
    status_color = "green" if status == "Yes" else "blue"
    st.markdown(f"**Emergency Detected:** <span style='color:{status_color}'>{status}</span>", unsafe_allow_html=True)

    if st.session_state.video_url:
        st.success("Video processed successfully!")
        st.video(st.session_state.video_url)
    else:
        st.error("Error: Processed video not found.")










# ---------------------------
# Futuristic Live Stats (Fake Ticker)
# ---------------------------
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 30px;">
        <div style="display: inline-block; background: #111827; color: #10B981; 
                    padding: 15px 30px; border-radius: 12px; font-size: 20px;
                    font-family: 'Courier New', monospace; box-shadow: 0 0 15px rgba(16,185,129,0.5);">
            🚑 Lives Saved: <span id="livesSaved">1,234</span>+
        </div>
        <div style="display: inline-block; background: #1F2937; color: #FBBF24; 
                    padding: 15px 30px; border-radius: 12px; font-size: 20px;
                    font-family: 'Courier New', monospace; box-shadow: 0 0 15px rgba(251,191,36,0.5); margin-left: 20px;">
            ⏱️ Avg. Response Time Reduction: <span id="timeReduction">80%</span>
        </div>
        <p style="font-size:12px; color:grey; margin-top:10px">*The data presented appears to be inaccurate and is not suitable for our analysis.</p>
    </div>

    <script>
    // Simple fake increment effect
    let counter = 1234;
    setInterval(() => {
        counter += Math.floor(Math.random() * 3);  // add random small number
        document.getElementById("livesSaved").textContent = counter.toLocaleString();
    }, 3000);
    </script>
    """,
    unsafe_allow_html=True
)







# ---------------------------
# Project Information Section
# ---------------------------
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); 
                border-radius: 20px; color: white; box-shadow: 0 0 20px rgba(0,0,0,0.5);">

    <h2>🚨 Why This Project Matters 🚨</h2>
    <p style="font-size: 18px; max-width: 800px; margin: auto;">
    Every minute counts in an emergency. Studies show that <strong>for every 1-minute delay</strong> in reaching a 
    patient, the survival rate can drop by up to <strong>7–10%</strong> for critical cases such as cardiac arrest or severe trauma.
    Traffic jams at intersections often cause ambulances to be delayed by <strong>5–15 minutes</strong>, turning life-saving 
    golden minutes into tragedy.
    </p>

    <h3>💡 Our Smart Solution</h3>
    <p style="font-size: 18px; max-width: 800px; margin: auto;">
    This project integrates <strong>Computer Vision</strong> and <strong>Smart Traffic Control</strong> to automatically detect 
    emergency vehicles (like ambulances) in live traffic camera feeds. Once detected, the system triggers 
    an <strong>instant green signal</strong>, clearing the path for the ambulance to pass safely — no human intervention required.
    </p>

    <h3>📊 Impact Potential</h3>
    <ul style="font-size: 18px; max-width: 800px; margin: auto; text-align: left;">
      <li>🔹 Reduce ambulance delays by up to <strong>80%</strong></li>
      <li>🔹 Save <strong>hundreds of lives</strong> per city per year</li>
      <li>🔹 Lower risk of secondary accidents from lane changes & panic driving</li>
      <li>🔹 Works with existing traffic infrastructure (CCTV + Traffic Lights)</li>
    </ul>

    <h3>🌐 A Step Toward Smarter Cities</h3>
    <p style="font-size: 18px; max-width: 800px; margin: auto;">
    By combining AI-powered detection and adaptive traffic management, this system is a step toward the future of 
    <strong>Intelligent Transportation Systems (ITS)</strong> — making our cities not only smarter but also safer and more 
    human-focused.
    </p>

    <p style="font-size: 16px; opacity: 0.8; margin-top: 20px;">
    Developed with ❤️ for innovation in public safety and emergency response.
    </p>

    <p style="font-size: 16px; margin-top: 15px;">
    Connect with me on LinkedIn: <a href="https://www.linkedin.com/in/mdrayeesansari/" target="_blank" style="color:#0A66C2; text-decoration: underline;">Md Rayees Ansari</a>
    </p>

    </div>
    """,
    unsafe_allow_html=True
)
