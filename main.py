from fastapi import FastAPI, Request
from fastapi.responses import Response
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="LLM Chaos Server")

# ⚙️ CONFIGURATION: Change this to control creativity!
# 0.0 = Deterministic/Consistent | 1.0 = Balanced | 1.5 = Chaotic | 2.0 = Maximum Creativity
TEMPERATURE = 0.0


def detect_content_type(content: str) -> tuple[str, str]:
    """Detect what type of content was generated"""
    content_lower = content.strip().lower()
    
    if content_lower.startswith('<!doctype html') or content_lower.startswith('<html'):
        return 'text/html', 'html'
    elif content_lower.startswith('{') or content_lower.startswith('['):
        return 'application/json', 'json'
    elif 'function' in content_lower or 'const ' in content_lower or 'var ' in content_lower:
        return 'application/javascript', 'js'
    elif content_lower.startswith('@') or ('{' in content and ':' in content and ';' in content):
        return 'text/css', 'css'
    else:
        return 'text/plain', 'text'


def clean_llm_response(content: str) -> str:
    """Remove markdown code blocks if present"""
    if "```" in content:
        parts = content.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Code block content
                lines = part.strip().split('\n')
                # Remove language identifier
                if lines[0].strip() in ['html', 'json', 'javascript', 'js', 'css', 'python', 'xml']:
                    return '\n'.join(lines[1:])
                return part.strip()
    return content


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all(request: Request, full_path: str):
    """Catch all routes and let LLM decide what to generate"""
    
    # Gather request information
    method = request.method
    query_params = dict(request.query_params)
    
    # Get request body if POST/PUT
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except:
            body = await request.body()
            body = body.decode() if body else None
    
    # Create prompt for LLM - pure and simple
    prompt = f"""You are a web server. A request has come in and you must generate the appropriate content.

REQUEST:
- Method: {method}
- Path: /{full_path}
- Query Parameters: {json.dumps(query_params, indent=2) if query_params else "None"}
- Request Body: {json.dumps(body, indent=2) if body else "None"}

YOUR TASK:
Analyze the path and generate appropriate content.

RULES:
- If path looks like a webpage (/, /home, /about, etc.) → generate complete HTML with CSS
- If path suggests API (/api/*, /data/*, *.json) → generate JSON data
- If path ends in .js → generate JavaScript code
- If path ends in .css → generate CSS code
- Return ONLY the content, no explanations or markdown

FOR HTML PAGES - MODERN WEBSITE:
- Use modern frameworks/libraries via CDN (public hosted URLs)
- Can include: Three.js, React, Vue, D3.js, GSAP, anime.js, particles.js, etc.
- Use CDN links like: unpkg.com, cdn.jsdelivr.net, cdnjs.cloudflare.com
- Example: <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
- Example: <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
- Create interactive, animated, beautiful modern UI with gradients, shadows, animations
- Make it functional and engaging with the CDN libraries

IMAGES & MEDIA:
- Always use public hosted images/media from: unsplash.com, picsum.photos, placeholder.com, or other free image services
- Example: https://picsum.photos/800/600 for random images
- Example: https://source.unsplash.com/random/800x600/?nature for themed images
- Never use local paths - only public URLs

ICONS:
- Always use public hosted icon libraries via CDN
- Font Awesome: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
- Bootstrap Icons: <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
- Or use SVG icons from: heroicons.com, feathericons.com
- Never use local icon files

Be creative, functional, and unpredictable!

Generate now:"""

    try:
        # Create model with configured temperature
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        generation_config = genai.types.GenerationConfig(
            temperature=TEMPERATURE
        )
        
        # Generate content using LLM
        response = model.generate_content(prompt, generation_config=generation_config)
        content = clean_llm_response(response.text)
        
        # Detect content type
        media_type, content_type = detect_content_type(content)
        
        return Response(content=content, media_type=media_type)
        
    except Exception as e:
        # Generate error page
        error_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 600px;
            margin: 100px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .error {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{ color: #e74c3c; margin: 0 0 20px 0; }}
        p {{ color: #666; line-height: 1.6; }}
        a {{ 
            color: #667eea; 
            text-decoration: none;
            font-weight: 600;
        }}
        a:hover {{ text-decoration: underline; }}
        .path {{ 
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="error">
        <h1>⚠️ Generation Failed</h1>
        <p><strong>Path:</strong></p>
        <div class="path">/{full_path}</div>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><a href="/">← Try Homepage</a></p>
    </div>
</body>
</html>"""
        return Response(content=error_html, media_type="text/html", status_code=500)


@app.on_event("startup")
async def startup_event():
    """Startup message"""
    print("\n🤖 LLM Chaos Server")
    print(f"🌡️  Temperature: {TEMPERATURE}")
    print("📡 Endpoint: http://localhost:8000")
    print("✅ Ready!\n")
