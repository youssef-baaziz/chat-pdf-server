
import streamlit as st
import base64


def get_image_base64(filepath: str) -> str:
    """
    filepath: path to the image. Must have a valid file extension.
    Returns: base64 encoded string of the image.
    """
    mime_type = filepath.split('.')[-1:][0].lower()
    with open(filepath, "rb") as f:
        content_bytes = f.read()
    content_b64encoded = base64.b64encode(content_bytes).decode()
    return f'data:image/{mime_type};base64,{content_b64encoded}'


css = """
<style>
.chat-message {
    padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex
}
.chat-message.user {
    background-color: #2b313e
}
.chat-message.bot {
    background-color: #475063;
}
.chat-message .avatar {
  width: 20%;
}
.chat-message .avatar img {
    max-width: 73px;
    max-height: 73px;
  border-radius: 50%;
  object-fit: cover;
}
.css-1li7dat{
    visibility: hidden;
}

.chat-message .message {
  width: 80%;
  padding: 0 1.5rem;
  color: #fff;
}
"""

bot_template = '''
<div class="chat-message bot">
    <div class="avatar"  style="min-height:110px;"  >
         <img src="{bot_image}" style="position:absolute;left:7px;max-width:110px; max-height:110px;">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''.format(bot_image=get_image_base64("robot.png"))

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="{user_image}">
    </div>    
    <div class="message">{{MSG}}</div>
</div>
'''.format(user_image=get_image_base64("client.png"))
