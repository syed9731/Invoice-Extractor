import openai
import base64
import streamlit as st

import json
import fitz
import logging


openai.api_key = st.secrets["openai"]["api_key"]  # Replace with your actual key


print("key here\n")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Streamlit app layout
st.title("Invoice Extractor")

# Section 1: Document upload
st.header("Upload a Document")
uploaded_file = st.file_uploader("Choose a file", type=["pdf"])

# Input for the 'excl' list
excl_input = st.text_area(
    "Exclude Columns",
    height=68,
    placeholder="Enter the columns to be excluded"
)

# Input for the 'lines' value
lines_input = st.number_input("Enter the number of lines:", min_value=1, value=1)

# Create the ChatCompletion request
def query_using_image(dynamic_prams):
    return openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Use the model which supports image input
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": f"""Extract product/service line_items from the provided image-based on the following parameters:
                      meta = {dynamic_params} #very important 
                        * Exclude columns listed in the meta.excl array from the response !important.
                        * response contains only the no of items specified in meta.lines  !important.
                                Instructions:
                                1. extract each and every columns
                                2. Return a JSON object in the defined output_format.
                                3. If token limits are exceeded, return:
                                   {{"extraction_status": false}}
                                4. valid output should be in format without any prefix/suffix like ```json```:
                                   {{"status":true,"data":[]}}
                                5. only data in tabular format is required
                                7. There can columns which contains sub columns in that case name a key as columnName_SubColumnName
                                8. If a subfield  is missing for a parent field, set its value to null in the JSON. Do not create the subfield if the parent field itself is entirely absent in the table.
                                8.If the table has columns that follow a hierarchical or grouped structure, create them as objects in the JSON. Dynamically group subfields under their respective parent fields 
                        """},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"  # Include the data as base64 within a URL
                        },
                    },
                ],
            }
        ],
        max_tokens=1500,
    )

def forming_dynamic_prompt(excl_input,lines_input):
    return f"{{excl:[{excl_input}],lines:{lines_input}}}"

def convert_pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    return images



if uploaded_file:
    with st.spinner("Converting PDF to images..."):
        temp_pdf_path = "temp_uploaded.pdf"
        with open(temp_pdf_path, "wb") as temp_file:
            temp_file.write(uploaded_file.read())


        images = convert_pdf_to_images(temp_pdf_path)
        for i, img_bytes in enumerate(images):
            # Instead of saving to a buffer, we directly base64 encode the image bytes
            encoded_image = base64.b64encode(img_bytes).decode("utf-8")

            # Forming dynamic params for your request
            dynamic_params = forming_dynamic_prompt(excl_input, lines_input)

            response = query_using_image(dynamic_params).choices[0]
            logger.info("Response generated successfully")
            logger.info(response)

    # data conversion
    content_string = response['message']['content']
    content_data = json.loads(content_string)
    invoice_details = content_data['data']



    status = content_data['status']

    if status:
        st.success("Extraction Successful! ✅")
    else:
        st.error("There is an error occurs during extraction-process system return with the status Failed! ❌")

    formatted_content = json.dumps(invoice_details, indent=4, ensure_ascii=False)

    # Convert the extracted data to a formatted JSON string
    st.text_area(
            "JSON Output",
            value=formatted_content,
            height=600,

        )