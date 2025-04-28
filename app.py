import streamlit as st
import json
import requests
from gtts import gTTS
from io import BytesIO
import speech_recognition as sr

# ----------------------
# Konfigurasi API LLM
API_KEY = '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'
API_URL = 'https://openrouter.ai/api/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# Inisialisasi session state
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'profile' not in st.session_state:
    st.session_state.profile = {}
if 'result_json' not in st.session_state:
    st.session_state.result_json = None
if 'questions' not in st.session_state:
    st.session_state.questions = []

# ----------------------
# Pilihan jumlah pertanyaan dan daftar pertanyaan
st.title("💬 Wawancara dan Analisis Kandidat")

# Step 1: Menentukan jumlah dan daftar pertanyaan
st.subheader("🔧 Pengaturan Wawancara")
num_questions = st.slider("Berapa banyak pertanyaan yang ingin Anda gunakan?", min_value=1, max_value=20, value=5)
custom_questions = []
for i in range(num_questions):
    question = st.text_input(f"Pertanyaan {i+1}: ", value=f"Pertanyaan {i+1}")
    custom_questions.append(question)

# Simpan pertanyaan yang dipilih ke dalam session state
st.session_state.questions = custom_questions

# Step 2: Menentukan prompt yang digunakan
st.subheader("📝 Pilih Prompt yang Digunakan")
prompt_option = st.radio("Pilih Prompt:", ("Default", "Custom"))

default_prompt = '''You are an expert in personality and behavioral assessment.
                 You will objectively analyze a candidate's answers to predefined interview questions.
                 Below is the candidate’s interview transcript and recording attempt data for your analysis:
                 Please provide the output **strictly in valid JSON** with the exact structure below (and no additional keys) (without writing 'json' at the beginning of the output):

{"candidate_name": "",
  "responses": [
    {"question_number": 1, "summary": "", "observed_traits": []},
    {"question_number": 2, "summary": "", "observed_traits": []},
    {"question_number": 3, "summary": "", "observed_traits": []},
    {"question_number": 4, "summary": "", "observed_traits": []},
    {"question_number": 5, "summary": "", "observed_traits": []},
    {"question_number": 6, "summary": "", "observed_traits": []},
    {"question_number": 7, "summary": "", "observed_traits": []},
    {"question_number": 8, "summary": "", "observed_traits": []},
    {"question_number": 9, "summary": "", "observed_traits": []}
  ],
  "analysis": {
    "key_strengths": [],
    "areas_for_improvement": [],
    "inconsistencies": []
  },
  "conclusion": ""}                     

'''

if prompt_option == "Default":
    prompt = default_prompt
else:
    prompt = st.text_input("masukan prompt yang di inginkan : ")

# ----------------------
# Formulir Data Pribadi
if st.session_state.current_question == 0:
    st.title("📄 Data Pribadi Kandidat")
    with st.form(key="form_data_pribadi"):
        nama = st.text_input("Nama Lengkap:")
        usia = st.text_input("Usia:")
        gender = st.radio("Jenis Kelamin:", ("Laki-laki", "Perempuan"))
        submit_profile = st.form_submit_button("▶️ Mulai Wawancara")

        if submit_profile and nama and usia and gender:
            st.session_state.profile = {
                'nama': nama,
                'usia': usia,
                'jenis_kelamin': gender
            }
            st.session_state.current_question = 1
            st.rerun()

# ----------------------
# Proses Wawancara
elif 1 <= st.session_state.current_question <= len(st.session_state.questions):
    idx = st.session_state.current_question - 1
    question = st.session_state.questions[idx]

    st.subheader(f"❓ Pertanyaan {idx+1}")
    st.markdown(f"**{question}**")

    tts = gTTS(question, lang='id')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    st.audio(buf, format='audio/mp3')

    audio = st.audio_input("🎙️ Jawaban Suara", key=f"audio_{idx}")
    text_answer = ""

    if audio:
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio) as source:
                audio_data = recognizer.record(source)
                text_answer = recognizer.recognize_google(audio_data, language="id-ID")
                st.success(f"Hasil STT: {text_answer}")
        except:
            st.warning("STT gagal dijalankan.")

    answer_input = st.text_area("📝 Jawaban Teks:", value=text_answer, key=f"text_{idx}")

    if st.button("➡️ Lanjut"):
        st.session_state.answers[question] = answer_input or text_answer or "-"
        st.session_state.current_question += 1
        st.rerun()

# ----------------------
# Kirim ke LLM
elif st.session_state.current_question > len(st.session_state.questions):
    st.success("✅ Semua pertanyaan selesai dijawab.")
    if st.button("📤 Kirim Jawaban ke LLM"):
        profil = st.session_state.profile
        jawaban = st.session_state.answers
        user_input = f"Nama: {profil['nama']}, Usia: {profil['usia']}, Gender: {profil['jenis_kelamin']}. Jawaban saya: " + \
                     " ".join([f"{i+1}. {q} - {a}" for i, (q, a) in enumerate(jawaban.items())])

        data = {
            "model": "deepseek/deepseek-chat:free",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ]
        }

        res = requests.post(API_URL, headers=headers, json=data)
        if res.status_code == 200:
            try:
                content = res.json()['choices'][0]['message']['content']
                st.subheader("🔍 Output Mentah dari LLM")
                st.code(content)
                # st.json(content)
                st.success("Sukses memproses JSON dari LLM")
            except:
                st.error("Gagal memproses JSON dari LLM.")
        else:
            st.error(f"Gagal dari API LLM: {res.status_code}")

# ----------------------
# Tampilkan Resume
if st.session_state.result_json:
    r = st.session_state.result_json
    st.title("🧾 Resume Hasil Wawancara")
    st.markdown(f"**Nama:** {r['candidate_name']}")
    st.markdown("### 🔍 Kekuatan Utama")
    for k in r['analysis']['key_strengths']:
        st.markdown(f"- {k}")
    st.markdown("### 🔧 Area Perbaikan")
    for w in r['analysis']['areas_for_improvement']:
        st.markdown(f"- {w}")
    st.markdown("### ⚠️ Inkonistensi")
    for inc in r['analysis']['inconsistencies']:
        st.markdown(f"- {inc}")
    st.markdown("### 📌 Kesimpulan")
    st.markdown(f"_{r['conclusion']}_")

# ----------------------
# Reset
if st.button("🔁 Ulangi Proses"):
    for k in ['current_question', 'answers', 'profile', 'result_json']:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()
