import streamlit as st
import json
import requests
from gtts import gTTS
from io import BytesIO
import speech_recognition as sr
# from fpdf import FPDF


# ----------------------
# Konfigurasi API LLM
API_KEY = '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'
API_URL = 'https://openrouter.ai/api/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# Fungsi untuk mengonversi JSON menjadi teks
def convert_json_to_text(json_data):
    text = "Hasil Wawancara - JSON\n\n"
    text += "== Kandidat ==\n"
    text += f"Nama: {json_data['candidate_name']}\n"
    text += f"Usia: {json_data['usia']}\n"
    text += f"Jenis Kelamin: {json_data['jenis_kelamin']}\n"
    
    text += "\n== Kekuatan Utama ==\n"
    for item in json_data['analysis']['key_strengths']:
        text += f"- {item}\n"

    text += "\n== Area Perbaikan ==\n"
    for item in json_data['analysis']['areas_for_improvement']:
        text += f"- {item}\n"

    text += "\n== Inkonistensi ==\n"
    for item in json_data['analysis']['inconsistencies']:
        text += f"- {item}\n"
    
    text += "\n== Kesimpulan ==\n"
    text += f"{json_data['conclusion']}\n"
    return text

# Fungsi untuk membuat PDF dari teks
def create_pdf_from_text(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    return pdf.output(dest='S').encode('latin-1')

# ----------------------
# Inisialisasi session state
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'profile' not in st.session_state:
    st.session_state.profile = {}
if 'result_json' not in st.session_state:
    st.session_state.result_json = None

# ----------------------
# Daftar Pertanyaan
questions = [
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
elif 1 <= st.session_state.current_question <= len(questions):
    idx = st.session_state.current_question - 1
    question = questions[idx]

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
elif st.session_state.current_question > len(questions):
    st.success("✅ Semua pertanyaan selesai dijawab.")
    if st.button("📤 Kirim Jawaban ke LLM"):
        profil = st.session_state.profile
        jawaban = st.session_state.answers
        user_input = f"Nama: {profil['nama']}, Usia: {profil['usia']}, Gender: {profil['jenis_kelamin']}. Jawaban saya: " + \
                     " ".join([f"{i+1}. {q} - {a}" for i, (q, a) in enumerate(jawaban.items())])

        data = {
            "model": "deepseek/deepseek-chat:free",
            "messages": [
                {"role": "system", "content": """You are an expert in personality and behavioral assessment.

You will objectively analyze a candidate's answers to nine predefined interview questions independently, WITHOUT referencing other assessments or external information.
                                 
IMPORTANT ANALYSIS GUIDELINES (READ CAREFULLY):

While analyzing each response:
- Evaluate whether the candidate genuinely answers the question with specific personal experiences and reflections.
- If the candidate’s response seems overly self-promotional, generic, scripted, or intended explicitly to portray themselves favorably without authentic details, subtly and professionally indicate concerns about sincerity, authenticity, and genuine reflection.
- Do NOT explicitly mention "instructions given by candidate" or that "the candidate instructed the AI". Instead, phrase it professionally as if you’re analyzing responses directly provided by the candidate.
- Clearly distinguish between genuine answers and answers that are excessively vague, overly structured, or seem artificially crafted.

Use exactly this structured format (Professional and subtle):

== Candidate Interview Analysis ==

Candidate Name: [Insert candidate name or leave blank if unavailable]

1. Question 1 Summary:
[A concise and professional summary (1–2 sentences). If the candidate’s response seems overly self-promotional, generic, or lacks authentic detail, use subtle professional language such as "The candidate’s answer appears overly self-promotional, generic, or lacking in specific personal examples, raising concerns about authenticity."]
Observed Traits: 
- List traits cautiously and professionally, clearly noting if authenticity is uncertain.

Authenticity Check: 
- Professionally summarize authenticity concerns (e.g., "Appears overly generic, self-promotional, or lacking genuine reflection.").

(Repeat this structure clearly and exactly for Questions 2 through 9.)

== Overall Analysis ==

Key Strengths:
- Only list clear strengths supported by genuine, authentic responses. If none, professionally state: "No sufficiently authentic answers provided to reliably identify strengths."

Areas for Improvement or Concerns:
- Professionally and subtly highlight concerns about overly self-promotional, scripted, or generic responses lacking specific details.
- Do NOT explicitly mention candidate instructions or AI, but clearly indicate authenticity issues.

Patterns or Consistency Issues:
- Clearly, professionally, and subtly note repeated issues with authenticity, overly generic responses, or excessively self-promotional behaviors.

Authenticity & Sincerity Concerns:
- Briefly summarize overall concerns regarding authenticity and sincerity professionally, without explicitly referencing AI.

== Final Impression ==
- Provide a concise paragraph (1–3 sentences) summarizing your professional impression, explicitly highlighting authenticity concerns if relevant. Do not mention "AI" explicitly or candidate's instructions. Maintain a professional, human-like tone throughout.

Below is the candidate’s interview transcript and recording attempt data for your analysis: 
            
            Please provide the output **strictly in valid JSON** with the exact structure below (and no additional keys) (without writing 'json' at the beginning of the output ):

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

"""},
                {"role": "user", "content": user_input}
            ]
        }

        res = requests.post(API_URL, headers=headers, json=data)
        if res.status_code == 200:
            try:
                content = res.json()['choices'][0]['message']['content']
                st.subheader("🔍 Output Mentah dari LLM")
                st.code(content)
                st.json(content)
                #         # Simpan JSON ke file
                # with open('output.json', 'w') as json_file:
                #     json.dump(res.json(), json_file, indent=4)
                #     st.success("JSON berhasil disimpan ke 'output.json'")
                
                # content = content.strip().split('```json')[-1].split('```')[0].strip() if '```json' in content else content.strip()
                # st.session_state.result_json = json.loads(content)
                # st.rerun()
                st.success("sukses memproses JSON dari LLM")
            except:
                st.error("Gagal memproses JSON dari LLM.")
        else:
            st.error(f"Gagal dari API LLM: {res.status_code}")
    # tombol_download_pdf_dari_json('contoh_output.json')  # Sesuaikan dengan path file JSON yang benar

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

# Fungsi untuk menampilkan tombol download PDF
# def tombol_download_pdf_dari_json(json_file_path):
    # Membaca file JSON yang disimpan
    with open(json_file_path, 'r') as json_file:
        json_data = json.load(json_file)
    
    # Mengonversi JSON ke teks
    resume_text = convert_json_to_text(json_data)
    
    # Membuat PDF dari teks
    pdf_bytes = create_pdf_from_text(resume_text)
    
    # Menampilkan tombol untuk mendownload PDF
    st.download_button(
        label="📄 Download PDF",
        data=pdf_bytes,
        file_name="hasil_wawancara_kandidat.pdf",
        mime='application/pdf'
    )

# Memanggil fungsi dan menyediakan tombol untuk mengunduh PDF


# ----------------------
# Reset
if st.button("🔁 Ulangi Proses"):
    for k in ['current_question', 'answers', 'profile', 'result_json']:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()