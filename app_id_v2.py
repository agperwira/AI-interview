import streamlit as st
import json
import requests
import speech_recognition as sr
from gtts import gTTS
from io import BytesIO

# -------------------------------
# Konfigurasi API OpenRouter
API_KEY = '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'
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
pertanyaan_wawancara = [
    "Ceritakan saat Anda harus mengatakan ‘tidak’ pada permintaan yang bertentangan dengan prioritas Anda dari seseorang yang dekat dengan anda. Bagaimana cara Anda menanganinya?",
    "Ceritakan tentang sebuah proyek di mana Anda harus memilih antara deadline atau hasil ideal anda",
    "Bagaimana Anda tetap termotivasi ketika kontribusi Anda kurang mendapat perhatian atau apresiasi?",
    "Ceritakan situasi di mana Anda harus memimpin atau mempengaruhi orang lain tanpa memiliki wewenang formal. Apa yang Anda lakukan?",
    "Ceritakan pengalaman saat anda mengambil keputusan yang berisiko baik di dunia kerja maupun di kehidupan pribadi, bagaimana Anda menimbang untung-ruginya?",
    "Bagaimana respon anda ketika anggota tim mengajukan ide yang cukup radikal namun bisa mempengaruhi proses kerja saat ini?",
    "Ceritakan bagaimana anda mengembangkan strategi untuk proyek jangka panjang. Langkah-langkah apa yang anda prioritaskan terlebih dahulu?",
    "Ceritakan saat anda harus beradaptasi pada sebuah lingkungan atau proses yang baru. Bagaimana anda menghadapinya?",
    "Ceritakan saat anda mendapatkan kritik yang tidak terduga atau cukup keras? Bagaimana anda menggunakannya untuk berkembang atau mengubah cara kerja anda?"
]

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

# -------------------------------
# Kirim dan Analisis ke LLM
if st.button('📤 Kirim Jawaban & Dapatkan Rangkuman'):
    input_pengguna = f"Berikut data pribadi saya: Nama: {data_jawaban['nama']}, Usia: {data_jawaban['usia']}, Jenis Kelamin: {data_jawaban['jenis_kelamin']}. " \
                     f"Berikut adalah jawaban saya atas pertanyaan wawancara: " + " ".join(
        [f"{i+1}. {q} - {a}" for i, (q, a) in enumerate(jawaban_kandidat.items())]
    )

    data = {
        "model": "deepseek/deepseek-chat:free",
        "messages": [
            {"role": "system", "content": 
             """You are an expert in personality and behavioral assessment.

Please provide the output **strictly in valid JSON** with the exact structure below (and no additional keys):

{
  "candidate_name": "",
  "responses": [
    {
      "question_number": 1,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 2,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 3,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 4,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 5,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 6,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 7,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 8,
      "summary": "",
      "observed_traits": []
    },
    {
      "question_number": 9,
      "summary": "",
      "observed_traits": []
    }
  ],
  "analysis": {
    "key_strengths": [],
    "areas_for_improvement": [],
    "inconsistencies": []
  },
  "conclusion": ""
}
"""
             },
            {"role": "user", "content": input_pengguna}
        ]
    }

    response = requests.post(API_URL, json=data, headers=headers)

    if response.status_code == 200:
        hasil = response.json()
        try:
            hasil_llm_json = json.loads(hasil['choices'][0]['message']['content'])
            st.session_state.hasil_llm_json = hasil_llm_json
            st.subheader("📄 Rangkuman Wawancara (Tampilan Rapi):")
            st.json(hasil_llm_json)
        except Exception as e:
            st.error("❌ Gagal memproses hasil JSON dari LLM.")
    else:
        st.error(f"❌ Gagal mendapatkan data dari API. Kode Status: {response.status_code}")

# -------------------------------
# Resume Otomatis
if st.button('🧾 Buat Resume Singkat dari Hasil Wawancara'):
    if st.session_state.hasil_llm_json is not None:
        data_resume = st.session_state.hasil_llm_json

        st.subheader("📋 Resume Wawancara Kandidat")
        st.markdown(f"**Nama Kandidat:** {data_resume.get('candidate_name', '-')}")

        st.markdown("### 🔍 Analisis Umum")
        st.markdown("**Kekuatan Utama:**")
        for strength in data_resume['analysis']['key_strengths']:
            st.markdown(f"- {strength}")

        st.markdown("**Area yang Perlu Ditingkatkan:**")
        for weakness in data_resume['analysis']['areas_for_improvement']:
            st.markdown(f"- {weakness}")

        st.markdown("**Inkonistensi atau Pola yang Menarik:**")
        for inc in data_resume['analysis']['inconsistencies']:
            st.markdown(f"- {inc}")

        st.markdown("### 🧠 Kesimpulan Akhir")
        st.markdown(f"_{data_resume['conclusion']}_")
    else:
        st.error("❌ Belum ada hasil wawancara yang tersedia.")
