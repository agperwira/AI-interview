import streamlit as st
import json
import requests
import speech_recognition as sr
from gtts import gTTS
from io import BytesIO

# -------------------------------
# Konfigurasi API OpenRouter
API_KEY = st.secrets['API_KEY']
API_URL = 'https://openrouter.ai/api/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# -------------------------------
# Session state untuk menyimpan hasil
if 'hasil_llm_json' not in st.session_state:
    st.session_state.hasil_llm_json = None

# -------------------------------
# Tampilan utama
st.title("🗣️ Wawancara Kandidat Kerja dengan Speech Recognition")

# -------------------------------
# Input Data Pribadi
data_jawaban = {}
data_jawaban['nama'] = st.text_input("Nama Lengkap:")
data_jawaban['usia'] = st.text_input("Usia:")
data_jawaban['jenis_kelamin'] = st.radio("Jenis Kelamin:", ('Laki-laki', 'Perempuan'))

# -------------------------------
# Daftar Pertanyaan
pertanyaan_wawancara = st.secrets['pertanyaan_wawancara']
# -------------------------------
# Form Jawaban
st.header("📝 Jawaban Wawancara Kandidat")
jawaban_kandidat = {}

for i, pertanyaan in enumerate(pertanyaan_wawancara, start=1):
    with st.expander(f"❓ Pertanyaan {i}"):
        st.markdown(f"**{pertanyaan}**")

        # TTS tanpa menyimpan file
        tts = gTTS(pertanyaan, lang='id')
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        st.audio(audio_buffer, format="audio/mp3")

        uploaded_audio = st.audio_input("Rekam jawaban:", key=f"audio_{pertanyaan}")
        jawaban_suara = ""

        if uploaded_audio is not None:
            try:
                recognizer = sr.Recognizer()
                with sr.AudioFile(uploaded_audio) as source:
                    audio_data = recognizer.record(source)
                    jawaban_suara = recognizer.recognize_google(audio_data, language="id-ID")
                    st.success(f"🎤 Hasil Speech-to-Text: {jawaban_suara}")
            except sr.UnknownValueError:
                st.error("❌ Tidak bisa mengenali suara.")
            except sr.RequestError:
                st.error("❌ Gagal mengakses layanan STT.")

        jawaban_teks = st.text_area("📝 Jawaban teks:", value=jawaban_suara, key=f"text_{i}")
        jawaban_kandidat[pertanyaan] = jawaban_teks if jawaban_teks else jawaban_suara

with st.expander('Masukan Prompt dan pilih model'):
    option = st.selectbox("How would you like to be contacted?",
                          ("deepseek-chat", 
                            #"bytedance-research",
                            #"google/gemini-2.5",
                            "deepseek/deepseek-r1"))
    prompt = st.selectbox('apakah anda ingin mengganti promt pada LLM? ', ('ya', 'gunakan default'))
    if propt == 'ya':
        prompt = st.text_area('Masukank Promp (pastikan prompt lengkap dan sesuai) :')
    else:
        promt == ("""You are an expert in personality and behavioral assessment.

You have a candidate’s interview transcript for nine predefined questions. 
You will analyze these responses independently, WITHOUT referencing any other assessments. 

Please return the output in a readable, structured text format that is easy to understand. Do NOT return JSON or code blocks. Follow the structure below exactly and use clear, professional language.

== Candidate Interview Analysis ==

Candidate Name: [Insert candidate name based on transcript or leave blank if not provided]

1. Question 1 Summary:
[Summarize the candidate's response]
Observed Traits: [List any relevant personality traits]

2. Question 2 Summary:
...

(continue through Question 9 in the same format)

== Overall Analysis ==
Key Strengths:
- [Bullet point strengths based on patterns in responses]

Areas for Improvement:
- [Bullet point areas where candidate could improve]

Inconsistencies or Patterns:
- [Bullet point any contradictions or notable behavioral patterns]

== Final Impression ==
[A short paragraph (1–3 sentences) giving your conclusion based only on the interview responses.]

Only use content from the transcript. If something is missing or unclear, simply leave it out or note that it's insufficient.

Below is the interview transcript:
""")

# Extract model name only
if option == "deepseek-chat":
    model_name = "deepseek/deepseek-chat:free"
elif option == "bytedance-research":
    model_name = "bytedance-research/ui-tars-72b:free"
elif option == "google/gemini-2.5":
    model_name = "google/gemini-2.5-pro-exp-03-25:free"
elif option == "deepseek/deepseek-r1":
    model_name = "deepseek/deepseek-r1-zero:free"
else:
    model_name = "Unknown"

# -------------------------------
# Kirim dan Analisis ke LLM
if st.button('📤 Kirim Jawaban & Dapatkan Rangkuman'):
    input_pengguna = f"Berikut data pribadi saya: Nama: {data_jawaban['nama']}, Usia: {data_jawaban['usia']}, Jenis Kelamin: {data_jawaban['jenis_kelamin']}. " \
                     f"Berikut adalah jawaban saya atas pertanyaan wawancara: " + " ".join(
        [f"{i+1}. {q} - {a}" for i, (q, a) in enumerate(jawaban_kandidat.items())]
    )

    data = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": prompt
            },
            {"role": "user", "content": input_pengguna}
        ]
    }

    response = requests.post(API_URL, json=data, headers=headers)

    if response.status_code == 200:
        hasil = response.json()
        try:
            teks_rangkuman = hasil['choices'][0]['message']['content']
            st.session_state.hasil_llm_teks = teks_rangkuman
            st.subheader("📄 Rangkuman Wawancara (Teks Naratif):")
            st.text(teks_rangkuman)
        except Exception as e:
            st.error("❌ Gagal memproses hasil teks dari LLM.")
    else:
        st.error(f"❌ Gagal mendapatkan data dari API. Kode Status: {response.status_code}")

# -------------------------------
# # Resume Otomatis
# if st.button('🧾 Buat Resume Singkat dari Hasil Wawancara'):
#     if st.session_state.hasil_llm_json is not None:
#         data_resume = st.session_state.hasil_llm_json

#         st.subheader("📋 Resume Wawancara Kandidat")
#         st.markdown(f"**Nama Kandidat:** {data_resume.get('candidate_name', '-')}")

#         st.markdown("### 🔍 Analisis Umum")
#         st.markdown("**Kekuatan Utama:**")
#         for strength in data_resume['analysis']['key_strengths']:
#             st.markdown(f"- {strength}")

#         st.markdown("**Area yang Perlu Ditingkatkan:**")
#         for weakness in data_resume['analysis']['areas_for_improvement']:
#             st.markdown(f"- {weakness}")

#         st.markdown("**Inkonistensi atau Pola yang Menarik:**")
#         for inc in data_resume['analysis']['inconsistencies']:
#             st.markdown(f"- {inc}")

#         st.markdown("### 🧠 Kesimpulan Akhir")
#         st.markdown(f"_{data_resume['conclusion']}_")
#     else:
#         st.error("❌ Belum ada hasil wawancara yang tersedia.")
