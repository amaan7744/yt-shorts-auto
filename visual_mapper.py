def sentence_to_visual(sentence: str):
    sentence = sentence.lower()

    if "car" in sentence and ("dead" in sentence or "dies" in sentence):
        return {
            "type": "image",
            "style": "3d_cartoon",
            "prompt": "3D cartoon style, man slumped dead in driver seat of car at night, cinematic lighting, dark mood"
        }

    if "home" in sentence or "apartment" in sentence:
        return {
            "type": "image",
            "style": "3d_cartoon",
            "prompt": "3D cartoon style, dark bedroom crime scene, bed, knife on floor, moody lighting"
        }

    if "police" in sentence or "arrest" in sentence:
        return {
            "type": "image",
            "style": "3d_cartoon",
            "prompt": "3D cartoon style, police officers arresting suspect at night, dramatic lighting"
        }

    return {
        "type": "image",
        "style": "3d_cartoon",
        "prompt": "3D cartoon crime scene illustration, cinematic lighting"
    }
