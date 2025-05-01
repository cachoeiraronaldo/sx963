from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mail import Mail, Message
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import re
import random
import string
from werkzeug.utils import secure_filename
import os
from PIL import Image
import json
import mercadopago
from decimal import Decimal, ROUND_HALF_UP
from flask_socketio import SocketIO, emit, rooms, send
from flask_socketio import join_room, leave_room
from typing import Optional
import time
import jwt
from datetime import datetime, timedelta, timezone
from flask import send_from_directory
import socket  
import os
from dotenv import load_dotenv
import filetype
import boto3
from botocore.exceptions import NoCredentialsError
import logging  # ← Pode importar aqui também, se ainda não tiver feito

# Setup de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.secret_key = 'd675013241f58f2bbe1b8dbbcf632c1f8e2f2a2556690ac4'
socketio = SocketIO(app)

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'sousa1000silva@gmail.com'
app.config['MAIL_PASSWORD'] = 'zflqeekugwmsccuu'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'sousa1000silva@gmail.com'

mail = Mail(app)

def resize_image(image_file, output_path, size):
    """Redimensiona uma imagem para caber nas dimensões especificadas."""
    image = Image.open(image_file)
    image.thumbnail(size, Image.ANTIALIAS)  # Redimensiona proporcionalmente
    image.save(output_path)  # Salva a imagem no caminho de destino
    
# Carrega o .env se existir (funciona local/localhost)
load_dotenv()

# Acessa a variável de ambiente
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")  # Note que é "ACCESS_TOKEN" (igual ao .env)

# Configura o SDK do Mercado Pago
sdk = mercadopago.SDK(ACCESS_TOKEN)

def get_db_connection():
    try:
        # Primeiro tenta pegar as variáveis do ambiente local (.env)
        # Se não tiver, usa as variáveis que o Railway fornece
        db_host = os.getenv('DB_HOST') or os.getenv('MYSQLHOST')
        db_name = os.getenv('DB_NAME') or os.getenv('MYSQLDATABASE')
        db_user = os.getenv('DB_USER') or os.getenv('MYSQLUSER')
        db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQLPASSWORD')
        db_port = os.getenv('DB_PORT') or os.getenv('MYSQLPORT')

        # Verifica se todas as variáveis estão definidas
        if not all([db_host, db_name, db_user, db_password, db_port]):
            raise ValueError("Uma ou mais variáveis de ambiente estão ausentes.")

        print("Variáveis de ambiente carregadas:")
        print(f"DB_HOST: {db_host}")
        print(f"DB_NAME: {db_name}")
        print(f"DB_USER: {db_user}")
        print(f"DB_PASSWORD: {'*' * len(db_password)}")  # Esconde a senha
        print(f"DB_PORT: {db_port}")

        # Faz a conexão
        conn = mysql.connector.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=int(db_port)
        )
        print("Conexão ao banco de dados bem-sucedida!")
        return conn

    except Exception as e:
        print("Erro ao conectar ao banco de dados:")
        print(f"Erro: {e}")
        raise

def is_vertical(filename):
    """Retorna True se o vídeo ou imagem for vertical."""
    if filename.endswith('.mp4') or filename.endswith('.jpg'):
        return "vertical" in filename  # Simulação para identificar vídeos verticais
    return False

def islower(char):
    return char.islower()

def generate_livekit_token(api_key: str, api_secret: str, identity: str, room: str, is_owner: bool = False) -> str:
    """Gera um token JWT para autenticação no LiveKit."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=6)
    
    grants = {
        "room": room,
        "roomJoin": True,
        "canPublish": is_owner,
        "canSubscribe": True,  # ESSENCIAL para espectadores
        "canPublishData": is_owner,
        "hidden": False,
        "roomAdmin": is_owner,
        "roomCreate": is_owner,
        "roomList": True,
        # Novas permissões para melhor controle
        "canUpdateOwnMetadata": True,
        "canSubscribeToOthers": True,
        "canSendData": True
    }
    
    payload = {
        "iss": api_key,
        "sub": identity,
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "video": grants,
        "name": identity,
        "metadata": ""  # Adicionado para evitar problemas
    }
    
    return jwt.encode(payload, api_secret, algorithm="HS256")

# Função para flash com tempo limite
def flash_with_timeout(message, category, timeout=12):
    flash(message, category)
    message_data = {'message': message, 'category': category, 'time': time.time(), 'timeout': timeout}
    app.jinja_env.globals['flash_message_data'] = message_data

# Função para verificar se o e-mail tem formato válido
def is_valid_email(email):
    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    return re.match(email_regex, email) is not None

# Função para gerar um código de verificação
def generate_verification_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def sanitize_input(text):
    if not text:
        return ''
    
    # 1. Remove tags HTML/XML (proteção contra XSS)
    text = re.sub(r'<[^>]*>', '', text)

    # 2. Remove caracteres perigosos comuns
    text = re.sub(r'[<>\"\'/\\|;]', '', text)

    # 3. Remove comandos SQL maliciosos explícitos (proteção adicional)
    text = re.sub(r'\b(drop|select|insert|delete|update|union|--|#)\b', '', text, flags=re.IGNORECASE)

    # 4. Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def upload_to_s3(file, filename):
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    try:
        s3.upload_fileobj(file, os.getenv('AWS_BUCKET_NAME'), filename)
        return f"https://{os.getenv('AWS_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{filename}"
    except NoCredentialsError:
        flash("Erro: Credenciais do S3 não encontradas.", 'error')
        return None

# Tamanhos máximos permitidos (em bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB para imagens
MAX_VIDEO_SIZE = 5 * 1024 * 1024 * 1024  # 5GB para vídeos (ajustável conforme necessário)

# Lista de extensões permitidas
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

def is_safe_file(file, allowed_extensions):
    """
    Verifica se um arquivo é seguro para upload.
    - Checa a extensão do arquivo.
    - Verifica o tipo MIME real do arquivo (usando filetype).
    - Previne ataques de path traversal.
    """
    if not file or not file.filename:
        return False

    # Extrai a extensão do arquivo
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()[1:]  # Pega a extensão sem o ponto

    # Verifica se a extensão está na lista permitida
    if ext not in allowed_extensions:
        return False

    # Previne path traversal
    if '..' in filename or filename.startswith('/'):
        return False

    # Lê os primeiros bytes do arquivo para verificar o tipo MIME real
    header = file.read(2048)  # Lê os primeiros 2KB
    file.seek(0)  # Volta o cursor do arquivo para o início

    kind = filetype.guess(header)
    if kind is None:
        return False  # Tipo de arquivo desconhecido

    # Verifica se o tipo MIME corresponde às extensões permitidas
    if kind.mime.startswith('image/') and ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False
    if kind.mime.startswith('video/') and ext not in ALLOWED_VIDEO_EXTENSIONS:
        return False

    return True

@app.route('/dashboard/<username>')
def dashboard(username):
    if 'username' not in session or 'user_id' not in session:
        flash("Você precisa estar logado para acessar o Perfil.", 'error')
        return redirect(url_for('index'))

    user_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 🔹 Função auxiliar para verificar se uma URL já está completa
        def is_complete_url(url):
            return url and (url.startswith("http://") or url.startswith("https://"))

        # Verifica se o criador está ao vivo
        cursor.execute("""
            SELECT is_live 
            FROM perfis_criadores 
            WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (username,))
        is_live_result = cursor.fetchone()
        is_live = is_live_result[0] if is_live_result else False  # Garante que is_live seja booleano

        # Verifica se o usuário logado é o criador do perfil
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
        creator = cursor.fetchone()
        cursor.fetchall()  # Limpa resultados pendentes

        if creator and creator[0] == user_id:
            is_owner = True  
        else:
            # Verifica se o usuário tem uma assinatura ativa para este criador
            cursor.execute("""
                SELECT status 
                FROM assinaturas 
                WHERE usuario_id = %s AND criador_assinado = %s AND status = 'ativo'
            """, (user_id, username))
            assinatura = cursor.fetchone()
            cursor.fetchall()  # Limpa resultados pendentes
            is_owner = False  

            if not assinatura:
                flash("Você precisa assinar este criador para acessar o perfil.", 'error')
                return redirect(url_for('creators_list'))  

        # Busca os dados do perfil do criador
        cursor.execute("""
            SELECT p.display_name, p.description, p.theme_color, p.profile_picture_url, p.cover_photo_url
            FROM perfis_criadores p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE u.nome_usuario = %s
        """, (username,))
        profile = cursor.fetchone()
        cursor.fetchall()  

        if not profile:
            flash("Perfil não encontrado.", 'error')
            return redirect(url_for('index'))

        # Converte URLs dos documentos apenas se não forem completas
        bucket_url = f"https://{os.getenv('AWS_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com"

        profile_picture_url = profile[3] if is_complete_url(profile[3]) else \
            f"{bucket_url}/profile_pictures/{profile[3]}" if profile[3] else None

        cover_photo_url = profile[4] if is_complete_url(profile[4]) else \
            f"{bucket_url}/cover_photos/{profile[4]}" if profile[4] else None

        # Busca mídias associadas ao perfil e verifica se o usuário pagou pelo vídeo
        cursor.execute("""
            SELECT m.filename, m.type, m.id, m.status, m.mensagem, m.categoria, m.valor_video, 
                CASE 
                    WHEN m.valor_video > 0 AND EXISTS (
                        SELECT 1 FROM videos_comprados vc WHERE vc.usuario_id = %s AND vc.media_id = m.id
                    ) THEN 'pago'
                    ELSE m.status
                END AS status_final
            FROM media m
            WHERE m.usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s) 
            AND m.status != 'excluido'
            AND m.categoria != 'trailer'
            AND m.is_free = FALSE
        """, (user_id, username))

        media_query_results = cursor.fetchall()

        # 🔐 Corrigido: evita erro de SQL se o criador ainda não tiver nenhuma mídia
        media_ids = [media[2] for media in media_query_results]
        participants_data = {}

        if media_ids:
            placeholders = ','.join(['%s'] * len(media_ids))
            cursor.execute(f"""
                SELECT mp.midia_id, GROUP_CONCAT(mp.nome_pessoa SEPARATOR '|||') AS participantes
                FROM midia_pessoas mp
                WHERE mp.midia_id IN ({placeholders})
                GROUP BY mp.midia_id
            """, media_ids)
            participants_data = {
                row[0]: row[1].split('|||') if row[1] else [] for row in cursor.fetchall()
            }

        # Processa as mídias
        media_files = []
        for media in media_query_results:
            aspect = "vertical" if is_vertical(media[0]) else "horizontal"
            media_id = media[2]

            # Converte a URL da mídia apenas se não for completa
            media_url = media[0] if is_complete_url(media[0]) else \
                f"{bucket_url}/media/{media[0]}" if media[0] else None

            media_files.append({
                "filename": media[0],
                "url": media_url,
                "type": media[1],
                "id": media_id,
                "status": media[7],
                "mensagem": media[4],
                "aspect": aspect,
                "categoria": media[5],
                "valor_video": media[6],
                "is_owner": is_owner,
                "participantes": participants_data.get(media_id, [])  # Adiciona participantes
            })

        # Busca número de assinantes e valor bruto total de assinaturas
        cursor.execute("""
            SELECT COUNT(*) as subscription_count, SUM(valor_pago) as total_revenue 
            FROM assinaturas 
            WHERE criador_assinado = %s AND status = 'ativo'
        """, (username,))
        subscription_info = cursor.fetchone()

        # Busca número de vídeos vendidos e faturamento total dos vídeos pagos
        cursor.execute("""
            SELECT COUNT(vc.id), COALESCE(SUM(m.valor_video), 0)
            FROM videos_comprados vc
            JOIN media m ON vc.media_id = m.id
            WHERE m.usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (username,))
        video_sales_info = cursor.fetchone()

        # Busca total de curtidas do criador
        cursor.execute("""
            SELECT COUNT(*) 
            FROM curtidas 
            WHERE criador_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (username,))
        total_likes = cursor.fetchone()[0]
          
        # Busca total de seguidores do criador
        cursor.execute("""
            SELECT COUNT(*) 
            FROM seguidores 
            WHERE criador_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (username,))
        total_followers = cursor.fetchone()[0]

        # Busca número de mensagens não lidas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM mensagens 
            WHERE destinatario_id = %s AND lida = FALSE
        """, (user_id,))
        unread_messages_count = cursor.fetchone()[0]  

        profile_data = {
            'display_name': profile[0],
            'description': profile[1],
            'theme_color': profile[2],
            'profile_picture_url': profile_picture_url,
            'cover_photo_url': cover_photo_url,
            'username': username,
            'is_live': is_live 
        }

        return render_template(
            'dashboard.html', 
            profile=profile_data, 
            media=media_files, 
            is_owner=is_owner, 
            subscription_count=subscription_info[0], 
            total_revenue=subscription_info[1] if subscription_info[1] else 0,
            videos_vendidos=video_sales_info[0], 
            total_video_revenue=video_sales_info[1],
            total_likes=total_likes,
            total_followers=total_followers,
            unread_messages_count=unread_messages_count,
            is_live=is_live  # Passa o status da live para o template
        )

    except Exception as e:
        print(f"❌ Erro no dashboard: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/profile')
def profile():
    if 'username' not in session:
        flash("Você precisa estar logado para acessar o perfil.", 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔹 Buscar ID do usuário logado
    cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (session['username'],))
    user_id = cursor.fetchone()

    if user_id:
        user_id = user_id[0]

        # 🔹 Buscar informações do criador
        cursor.execute("""
            SELECT u.nome_usuario, p.display_name, p.description, p.theme_color, 
                   p.profile_picture_url, p.cover_photo_url, p.valor_assinatura
            FROM usuarios u
            JOIN perfis_criadores p ON u.id = p.usuario_id
            WHERE u.id = %s
        """, (user_id,))
        user_info = cursor.fetchone()

        # 🔹 Buscar mídias do criador
        cursor.execute("""
            SELECT filename, type FROM media WHERE usuario_id = %s
        """, (user_id,))
        media_files = cursor.fetchall()
        media = [{'filename': file[0], 'type': file[1]} for file in media_files]

        # 🔹 Buscar vídeo mais recente
        cursor.execute("""
            SELECT filename, status, mensagem FROM media 
            WHERE usuario_id = %s AND type = 'video' LIMIT 1
        """, (user_id,))
        video = cursor.fetchone()

        # 🔹 Buscar faturamento por assinaturas válidas no período atual
        cursor.execute("""
            SELECT COUNT(*) as subscription_count, COALESCE(SUM(valor_pago), 0) as total_revenue
            FROM assinaturas 
            WHERE criador_assinado = %s
            AND status = 'ativo'
            AND NOW() BETWEEN data_inicio AND data_fim

        """, (session['username'],))

        subscription_info = cursor.fetchone()

        mes_atual = datetime.now().strftime("%Y-%m")  # Obtém "YYYY-MM"

        cursor.execute("""
            SELECT COUNT(vc.id), COALESCE(SUM(m.valor_video), 0)
            FROM videos_comprados vc
            JOIN media m ON vc.media_id = m.id
            WHERE m.usuario_id = %s
            AND vc.mes_ano = %s
        """, (user_id, mes_atual))
        video_sales_info = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(vc.id), COALESCE(SUM(m.valor_video), 0)
            FROM videos_comprados vc
            JOIN media m ON vc.media_id = m.id
            WHERE m.usuario_id = %s
            AND vc.mes_ano = %s
        """, (user_id, mes_atual))
        video_sales_info = cursor.fetchone()

        # Calcular mês anterior
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1)
        mes_anterior = (primeiro_dia_mes - timedelta(days=1)).strftime("%Y-%m")

        # Buscar o acerto do mês anterior
        cursor.execute("""
            SELECT id, mes_ano, total_assinaturas, total_videos, status
            FROM acertos_mensais
            WHERE usuario_id = %s AND mes_ano = %s
            LIMIT 1
        """, (user_id, mes_anterior))
        acerto = cursor.fetchone()

        #🔹 Buscar número de assinaturas ativas
        cursor.execute("""
            SELECT COUNT(*)
            FROM assinaturas
            WHERE criador_assinado = %s
              AND status = 'ativo'
              AND CURDATE() BETWEEN data_inicio AND data_fim
        """, (session['username'],))
        active_subscriptions = cursor.fetchone()[0] 

        # 🔹 Calcular saldo líquido
        total_revenue = Decimal(str(subscription_info[1])) if subscription_info[1] else Decimal('0.00')
        total_video_revenue = Decimal(str(video_sales_info[1])) if video_sales_info[1] else Decimal('0.00')
        total_bruto = total_revenue + total_video_revenue
        saldo_liquido = (total_bruto * Decimal('0.75')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        cursor.close()
        conn.close()

        return render_template(
            'profile.html',
            user_info=user_info,
            media=media,
            video_filename=video[0] if video else None,
            video_status=video[1] if video else None,
            video_mensagem=video[2] if video else None,
            subscription_count=subscription_info[0],
            total_revenue=total_revenue,
            videos_vendidos=video_sales_info[0],
            total_video_revenue=total_video_revenue,
            saldo_liquido=saldo_liquido,
            acerto_id=acerto[0] if acerto else None,
            mes_ano=acerto[1] if acerto else None,
            valor_assinaturas=acerto[2] if acerto else Decimal('0.00'),
            valor_videos=acerto[3] if acerto else Decimal('0.00'),
            status_acerto=acerto[4] if acerto else 'pendente',
            acerto_mes_anterior=acerto,  # ✅ Adiciona isso!
            active_subscriptions=active_subscriptions  # Passando o número de assinaturas ativas
        )
    
    else:
        cursor.close()
        conn.close()
        flash("Usuário não encontrado.", 'error')
        return redirect(url_for('index'))

@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        flash("Você precisa estar logado para atualizar o perfil.", 'error')
        return redirect(url_for('index'))

    # Captura os dados do formulário com sanitização
    display_name = sanitize_input(request.form.get('display_name'))
    description = sanitize_input(request.form.get('description'))
    theme_color = request.form.get('theme_color')  # Sanitiza a cor do tema
    profile_picture = request.files.get('profile_picture')
    cover_photo = request.files.get('cover_photo')
    media_photos = request.files.getlist('media_photos')  # Para múltiplas fotos
    media_videos = request.files.getlist('media_videos')  # Para múltiplos vídeos
    video_value = request.form.get('video_value', '0.00')  # Padrão 0.00 se estiver vazio
    video_value = float(video_value) if video_value else 0.00  # Converte corretamente

    # Conectar ao banco de dados
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obter os dados atuais do perfil
    cursor.execute("""
        SELECT display_name, description, theme_color, profile_picture_url, cover_photo_url
        FROM perfis_criadores
        WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
    """, (session['username'],))
    current_data = list(cursor.fetchone())  # Converte a tupla em uma lista

    # Atualizar os campos apenas se novos valores foram fornecidos
    if display_name:
        current_data[0] = display_name  # Atualiza o nome de exibição
    if description:
        current_data[1] = description  # Atualiza a descrição
    if theme_color:
        current_data[2] = theme_color  # Atualiza a cor do tema

    # Atualizar a imagem de perfil se fornecida (USANDO A FUNÇÃO ATUALIZADA)
    if profile_picture:
        profile_picture_filename = secure_filename(profile_picture.filename)

        if not is_safe_file(profile_picture, ALLOWED_IMAGE_EXTENSIONS):
            flash("Formato de imagem inválido ou arquivo corrompido.", 'error')
            return redirect(url_for('profile'))

        # Verificação de tamanho
        profile_picture.seek(0, 2)  # Move o ponteiro para o final do arquivo
        profile_picture_size = profile_picture.tell()
        profile_picture.seek(0)  # Reset file pointer

        if profile_picture_size > MAX_IMAGE_SIZE:
            flash("Imagem muito grande. Máximo 10MB permitido.", 'error')
            return redirect(url_for('profile'))

        # Salvar a imagem
        profile_picture_url = upload_to_s3(profile_picture, f"profile_pictures/{profile_picture_filename}")
        if not profile_picture_url:
            flash("Erro ao fazer upload da imagem de perfil.", 'error')
            return redirect(url_for('profile'))
        current_data[3] = profile_picture_url  # Atualiza a URL da imagem de perfil

    # Atualizar a imagem de capa se fornecida (USANDO A FUNÇÃO ATUALIZADA)
    if cover_photo:
        cover_photo_filename = secure_filename(cover_photo.filename)

        if not is_safe_file(cover_photo, ALLOWED_IMAGE_EXTENSIONS):
            flash("Formato de imagem de capa inválido ou tipo de conteúdo não corresponde. Permitido: PNG, JPG, GIF.", 'error')
            return redirect(url_for('profile'))

        # Verificação de tamanho
        cover_photo.seek(0, 2)  # Move o ponteiro para o final do arquivo
        cover_photo_size = cover_photo.tell()
        cover_photo.seek(0)  # Reset file pointer

        if cover_photo_size > MAX_IMAGE_SIZE:
            flash("Imagem de capa muito grande. Máximo 10MB permitido.", 'error')
            return redirect(url_for('profile'))

        # Salvar a imagem de capa
        cover_photo_url = upload_to_s3(cover_photo, f"cover_photos/{cover_photo_filename}")
        if not cover_photo_url:
            flash("Erro ao fazer upload da imagem de capa.", 'error')
            return redirect(url_for('profile'))
        current_data[4] = cover_photo_url  # Atualiza a URL da imagem de capa

    # Obter o ID do usuário
    cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (session['username'],))
    user_id = cursor.fetchone()[0]

    # Salvar múltiplas fotos (USANDO A FUNÇÃO ATUALIZADA)
    for photo in media_photos:
        if photo:
            photo_filename = secure_filename(photo.filename)

            if not is_safe_file(photo, ALLOWED_IMAGE_EXTENSIONS):
                flash("Formato de foto inválido ou tipo de conteúdo não corresponde. Permitido: PNG, JPG, GIF.", 'error')
                return redirect(url_for('profile'))

            # Verificação de tamanho
            photo.seek(0, 2)  # Move o ponteiro para o final do arquivo
            photo_size = photo.tell()
            photo.seek(0)  # Reset file pointer

            if photo_size > MAX_IMAGE_SIZE:
                flash("Foto muito grande. Máximo 10MB permitido.", 'error')
                return redirect(url_for('profile'))

            # Salvar a foto
            photo_url = upload_to_s3(photo, f"media/photos/{photo_filename}")
            if not photo_url:
                flash("Erro ao fazer upload da foto.", 'error')
                return redirect(url_for('profile'))
            cursor.execute("""
                INSERT INTO media (usuario_id, filename, type, status, categoria, mensagem)
                VALUES (%s, %s, 'image', 'pendente', 'perfil', NULL)
            """, (user_id, photo_url))  # Salva a URL completa no banco de dados

            media_id = cursor.lastrowid  # Obtém o ID da mídia inserida

            # Inserir participantes da foto (se houver)
            participantes_fotos = request.form.getlist('participantes_fotos[]')
            for i, photo in enumerate(media_photos):
                if participantes_fotos and len(participantes_fotos) > i:
                    nomes = [sanitize_input(nome.strip()) for nome in participantes_fotos[i].split(',') if nome.strip()]
                    for nome in nomes:
                        cursor.execute(
                            "INSERT INTO midia_pessoas (midia_id, nome_pessoa) VALUES (%s, %s)",
                            (media_id, nome)
                        )

            # Emitir evento via socket.io
            socketio.emit("nova_midia_admin", {
                "usuario_id": user_id,
                "mensagem": f"📷 Nova foto enviada por @{session['username']}. Aguardando aprovação.",
                "midia": {
                    "id": media_id,
                    "filename": photo_filename,
                    "type": "image",
                    "categoria": "perfil",
                    "descricao": None,
                    "participantes": nomes if 'nomes' in locals() else []  # Adiciona os participantes
                }
            })

    # Obtém o mês e o ano atuais no formato "YYYY-MM"
    mes_ano_atual = datetime.now().strftime('%Y-%m')

    # Salvar múltiplos vídeos (USANDO A FUNÇÃO ATUALIZADA)
    for video in media_videos:
        if video:
            video_filename = secure_filename(video.filename)

            if not is_safe_file(video, ALLOWED_VIDEO_EXTENSIONS):
                flash("Formato de vídeo inválido.", 'error')
                return redirect(url_for('profile'))

            # Verificação de tamanho
            video.seek(0, 2)  # Move o ponteiro para o final do arquivo
            file_size = video.tell()  # Obtém o tamanho do arquivo
            video.seek(0)  # Reset file pointer

            if file_size > MAX_VIDEO_SIZE:
                flash("Vídeo muito grande. Máximo 5GB permitido.", 'error')
                return redirect(url_for('profile'))

            # Salvar o vídeo
            video_url = upload_to_s3(video, f"media/videos/{video_filename}")
            if not video_url:
                flash("Erro ao fazer upload do vídeo.", 'error')
                return redirect(url_for('profile'))
            cursor.execute("""
                INSERT INTO media (usuario_id, filename, type, status, categoria, mensagem, valor_video, mes_ano)
                VALUES (%s, %s, 'video', 'pendente', 'perfil', NULL, %s, %s)
            """, (user_id, video_url, video_value if video_value else 0.00, mes_ano_atual))  # Salva a URL completa no banco de dados

            media_id = cursor.lastrowid  # Obtém o ID do vídeo inserido

            # Inserir participantes do vídeo (se houver)
            participantes_videos = request.form.getlist('participantes_videos[]')
            for i, video in enumerate(media_videos):
                if participantes_videos and len(participantes_videos) > i:
                    nomes = [sanitize_input(nome.strip()) for nome in participantes_videos[i].split(',') if nome.strip()]
                    for nome in nomes:
                        cursor.execute(
                            "INSERT INTO midia_pessoas (midia_id, nome_pessoa) VALUES (%s, %s)",
                            (media_id, nome)
                        )

            # Emitir evento via socket.io
            socketio.emit("nova_midia_admin", {
                "usuario_id": user_id,
                "mensagem": f"🎥 Novo vídeo enviado por @{session['username']}. Aguardando aprovação.",
                "midia": {
                    "id": media_id,
                    "filename": video_filename,
                    "type": "video",
                    "categoria": "perfil",
                    "descricao": None,
                    "participantes": nomes if 'nomes' in locals() else []  # Adiciona os participantes
                }
            })

    # Atualizar os dados do perfil no banco de dados
    cursor.execute("""
        UPDATE perfis_criadores
        SET display_name = %s, description = %s, theme_color = %s, profile_picture_url = %s, cover_photo_url = %s
        WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
    """, (current_data[0], current_data[1], current_data[2], current_data[3], current_data[4], session['username']))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Perfil atualizado com sucesso!", 'success')
    return redirect(url_for('profile'))

@app.route('/delete_media/<int:media_id>', methods=['POST'])
def delete_media(media_id):
    if 'username' not in session:
        flash("Você precisa estar logado para excluir a mídia.", 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Obter o arquivo associado à entrada específica (MANTIDO)
        cursor.execute("""
            SELECT filename FROM media 
            WHERE id = %s AND usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (media_id, session['username']))
        media = cursor.fetchone()

        if media:
            filename = media[0]
            print(f"Excluindo a mídia: ID = {media_id}, Nome do arquivo = {filename}")

            # --- NOVO: Excluir registros de participantes (midia_pessoas) ---
            cursor.execute("DELETE FROM midia_pessoas WHERE midia_id = %s", (media_id,))
            print(f"Participantes da mídia {media_id} removidos.")

            # --- NOVO: Excluir registros de compras (videos_comprados) ---
            cursor.execute("DELETE FROM videos_comprados WHERE media_id = %s", (media_id,))
            print(f"Compras associadas à mídia {media_id} removidas.")

            # Verificar se a mídia está sendo usada em outro lugar (MANTIDO)
            cursor.execute("""
                SELECT COUNT(*) FROM media 
                WHERE filename = %s AND id != %s
            """, (filename, media_id))
            count = cursor.fetchone()[0]

            if count == 0:
                # Excluir o arquivo físico (MANTIDO)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'media', filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Arquivo {filename} excluído com sucesso.")
                else:
                    print(f"Arquivo {filename} não encontrado.")

            # Excluir a entrada do banco de dados (MANTIDO)
            cursor.execute("DELETE FROM media WHERE id = %s", (media_id,))
            conn.commit()
            flash("Mídia excluída com sucesso!", 'success')
        else:
            flash("Mídia não encontrada ou você não tem permissão para excluí-la.", 'error')

    except Exception as e:
        conn.rollback()  # Adicionado para segurança
        flash(f"Erro ao excluir a mídia: {str(e)}", 'error')
        print(f"Erro durante a exclusão: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    # Redirecionamento mantido
    referrer = request.referrer
    if referrer and 'dashboard' in referrer:
        return redirect(url_for('dashboard', username=session['username']))
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'HEAD'])
def index():
    if request.method == 'HEAD':
        return '', 200  # Resposta vazia para HEAD

    user_initials = session.get('user_initials')

    # Conectar ao banco de dados
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta para criadores - corrigida para incluir p.is_live
    cursor.execute("""
        SELECT u.nome_usuario, p.profile_picture_url, p.cover_photo_url, p.is_live
        FROM perfis_criadores p 
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE u.status = 'verificado' AND u.status_verificacao = 'verificado'
    """)
    creators = cursor.fetchall()

    # Consulta para mídias gratuitas - corrigida para incluir p.is_live
    cursor.execute("""
        SELECT m.id, m.categoria, u.nome_usuario, m.filename, m.title, m.description, m.type, 
               p.profile_picture_url, m.views, p.is_live
        FROM media m
        JOIN usuarios u ON m.usuario_id = u.id
        JOIN perfis_criadores p ON u.id = p.usuario_id
        WHERE m.status = 'disponivel' AND m.is_free = TRUE 
        AND m.categoria IN ('anal', 'boquete', 'casal', 'novinha', 'orgia', 'solo', 'suruba', 'trisal')
    """)
    free_media = cursor.fetchall()

    # Consulta para trailers - modificada para incluir participantes
    cursor.execute("""
        SELECT m.id, m.filename, m.title, m.description, p.profile_picture_url, u.nome_usuario, p.is_live
        FROM media m 
        JOIN usuarios u ON m.usuario_id = u.id
        JOIN perfis_criadores p ON u.id = p.usuario_id
        WHERE m.status = 'disponivel' AND m.categoria = 'trailer'
    """)
    trailers = cursor.fetchall()

    # Consulta para participantes dos trailers
    trailer_ids = [trailer[0] for trailer in trailers]
    trailer_participants = {}
    if trailer_ids:
        placeholders = ','.join(['%s'] * len(trailer_ids))
        cursor.execute(f"""
            SELECT mp.midia_id, GROUP_CONCAT(mp.nome_pessoa SEPARATOR '|||') AS participantes
            FROM midia_pessoas mp
            WHERE mp.midia_id IN ({placeholders})
            GROUP BY mp.midia_id
        """, trailer_ids)
        trailer_participants = {
            row[0]: [sanitize_input(nome.strip()) for nome in row[1].split('|||') if nome.strip()]
            for row in cursor.fetchall()
        }

    # Consulta para participantes
    media_ids = [media[0] for media in free_media]  # IDs das mídias gratuitas
    participants_data = {}
    if media_ids:
        placeholders = ','.join(['%s'] * len(media_ids))  # Cria placeholders para os IDs
        cursor.execute(f"""
            SELECT mp.midia_id, GROUP_CONCAT(mp.nome_pessoa SEPARATOR '|||') AS participantes
            FROM midia_pessoas mp
            WHERE mp.midia_id IN ({placeholders})
            GROUP BY mp.midia_id
        """, media_ids)
        participants_data = {
            row[0]: [sanitize_input(nome.strip()) for nome in row[1].split('|||') if nome.strip()]
            for row in cursor.fetchall()
        }

    # Organizar as mídias por categoria
    categorized_media = {
        'anal': [],
        'boquete': [],
        'casal': [],
        'novinha': [],
        'orgia': [],
        'solo': [],
        'suruba': [],
        'trisal': []
    }

    for media in free_media:
        media_id, categoria, nome_usuario, filename, title, description, media_type, user_profile, views, is_live = media
        categorized_media[categoria].append({
            'id': media_id,
            'nome_usuario': nome_usuario,
            'filename': filename,
            'title': title,
            'description': description,
            'type': media_type,
            'profile_picture_url': user_profile if user_profile else 'default_profile_picture.jpg',
            'views': views,
            'is_live': is_live,
            'participantes': participants_data.get(media_id, [])  # Adiciona participantes
        })

    cursor.close()
    conn.close()

    return render_template('index.html', 
                         user_initials=user_initials, 
                         creators=creators, 
                         categorized_media=categorized_media, 
                         trailers=trailers,
                         trailer_participants=trailer_participants)
    
@app.route('/signup', methods=['POST'])
def signup():
    username = sanitize_input(request.form['username'])
    email = sanitize_input(request.form['email'])
    password = request.form['password']
    password_confirmation = request.form['password-confirmation']

    # Verificar se o e-mail é válido
    if not is_valid_email(email):
        flash_with_timeout("E-mail inválido.", 'error')
        return redirect(url_for('index'))

    if password != password_confirmation:
        flash_with_timeout("As senhas não coincidem", 'error')
        return redirect(url_for('index'))

    if not username or not email or not password:
        flash_with_timeout("Preencha todos os campos", 'error')
        return redirect(url_for('index'))

    # Verificar se o nome de usuário já existe
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        flash_with_timeout("Nome de usuário já existe. Tente outro.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))

    hashed_password = generate_password_hash(password)
    verification_code = generate_verification_code()

    try:
        cursor.execute(
            "INSERT INTO usuarios (nome_usuario, email, senha, tipo_usuario, status, codigo_verificacao) VALUES (%s, %s, %s, %s, %s, %s)",
            (username, email, hashed_password, 'usuario', 'nao_verificado', verification_code)
        )
        conn.commit()

        # Enviar e-mail de verificação
        msg = Message('Verificação de E-mail', recipients=[email])
        msg.body = f'Seu código de verificação é: {verification_code}'
        mail.send(msg)

        # Armazenar o e-mail na sessão para ser usado na página de verificação
        session['user_email'] = email  # Armazena o e-mail na sessão
        session['verification_pending'] = True  # Avisa que o e-mail precisa ser verificado
        
        flash_with_timeout("Cadastro realizado! Verifique seu e-mail para concluir.", 'success')

    except mysql.connector.IntegrityError:
        flash_with_timeout("Email já cadastrado.", 'error')
    except Exception as e:
        flash_with_timeout(f"Ocorreu um erro: {str(e)}", 'error')

    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/close_verification')
def close_verification():
    session.pop('verification_pending', None)  # Remove a verificação pendente
    return redirect(url_for('index'))

@app.route('/verify_email/<email>', methods=['GET', 'POST'])
def verify_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Busca o código de verificação no banco
    cursor.execute("SELECT codigo_verificacao FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    if request.method == 'POST':
        verification_code = request.form['verification_code']

        if user:
            if user[0] == verification_code:
                # ✅ Verificação bem-sucedida: atualiza status
                cursor.execute("UPDATE usuarios SET status = 'verificado' WHERE email = %s", (email,))
                conn.commit()

                # ✅ Dispara notificação para admin
                cursor.execute("""
                    SELECT u.id, u.nome_usuario, u.documento_frente_url, u.documento_verso_url, u.cpf,
                           u.documento_rosto_url, u.status_verificacao, p.valor_assinatura
                    FROM usuarios u
                    LEFT JOIN perfis_criadores p ON u.id = p.usuario_id
                    WHERE u.email = %s
                """, (email,))
                usuario = cursor.fetchone()

                if usuario:
                    socketio.emit("novo_usuario_admin", {
                        "id": usuario[0],
                        "nome_usuario": usuario[1],
                        "cpf": usuario[4],
                        "documento_frente_url": usuario[2],
                        "documento_verso_url": usuario[3],
                        "documento_rosto_url": usuario[5],
                        "valor_assinatura": str(usuario[7]),
                        "mensagem": f"✅ Novo criador de conteúdo verificado: @{usuario[1]}"
                    })

                flash_with_timeout("E-mail verificado com sucesso!", 'success')
                session.pop('verification_pending', None)  # 🔓 Agora sim remove o modal
            else:
                flash_with_timeout("Código de verificação inválido.", 'error')
                # ❌ Não remove session['verification_pending']
        else:
            flash_with_timeout("E-mail não encontrado no banco de dados.", 'error')
            # ❌ Também não remove session — deixa tentar novamente

    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username_or_email = sanitize_input(request.form['login-username'])  # ✅ Protege contra injeção
    password = request.form['login-password']

    print(f"Tentando fazer login com: {username_or_email}")  # Debugging

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome_usuario, senha, tipo_usuario, status FROM usuarios WHERE email = %s OR nome_usuario = %s", 
                   (username_or_email, username_or_email))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        if user[4] != 'verificado':  
            flash_with_timeout("Conta não verificada. Verifique seu e-mail.", 'error')
            return redirect(url_for('index'))

        if check_password_hash(user[2], password):  
            flash_with_timeout("Login bem-sucedido!", 'success')
            
            # 🔹 Agora armazenamos o ID do usuário na sessão também!
            session['username'] = user[1]  # Armazena o nome de usuário completo
            session['user_initials'] = user[1][0].upper()  
            session['user_id'] = user[0]  # ✅ Armazena o ID do usuário na sessão

            print(f"Usuário logado: {session}")  # Debugging - Verifica se a sessão está certa

            if user[3] == 'criador':  
                return redirect(url_for('profile'))  
            else:
                return redirect(url_for('index'))  

    flash_with_timeout("Nome de usuário ou senha incorretos.", 'error')
    return redirect(url_for('index'))

@app.route('/signup_creator', methods=['POST'])
def signup_creator():
    # Captura os dados do formulário com sanitização
    username = sanitize_input(request.form['username'])
    email = sanitize_input(request.form['email'])
    password = request.form['password']
    password_confirmation = request.form['password-confirmation']
    profile_picture = request.files['profile_picture']
    cover_photo = request.files['cover_photo']
    documento_frente = request.files['documento_frente']
    documento_verso = request.files['documento_verso']
    documento_rosto = request.files['documento_rosto']
    cpf = sanitize_input(request.form['cpf'])

    # Verificar se o e-mail é válido
    if not is_valid_email(email):
        flash_with_timeout("E-mail inválido.", 'error')
        return redirect(url_for('index'))

    if password != password_confirmation:
        flash_with_timeout("As senhas não coincidem", 'error')
        return redirect(url_for('index'))

    if not username or not email or not password:
        flash_with_timeout("Preencha todos os campos", 'error')
        return redirect(url_for('index'))

    # Verificar se o nome de usuário já existe
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        flash_with_timeout("Nome de usuário já existe. Tente outro.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))

    hashed_password = generate_password_hash(password)
    verification_code = generate_verification_code()

    try:
        # Salvar a imagem de perfil no S3
        profile_picture_url = None
        if profile_picture:
            profile_picture_filename = secure_filename(profile_picture.filename)

            if not is_safe_file(profile_picture, ALLOWED_IMAGE_EXTENSIONS):
                flash_with_timeout("Formato de imagem de perfil inválido ou arquivo corrompido.", 'error')
                return redirect(url_for('index'))

            profile_picture_url = upload_to_s3(profile_picture, f"profile_pictures/{profile_picture_filename}")
            if not profile_picture_url:
                flash_with_timeout("Erro ao fazer upload da imagem de perfil.", 'error')
                return redirect(url_for('index'))

        # Salvar a imagem de capa no S3
        cover_photo_url = None
        if cover_photo:
            cover_photo_filename = secure_filename(cover_photo.filename)

            if not is_safe_file(cover_photo, ALLOWED_IMAGE_EXTENSIONS):
                flash_with_timeout("Formato de imagem de capa inválido ou arquivo corrompido.", 'error')
                return redirect(url_for('index'))

            cover_photo_url = upload_to_s3(cover_photo, f"cover_photos/{cover_photo_filename}")
            if not cover_photo_url:
                flash_with_timeout("Erro ao fazer upload da imagem de capa.", 'error')
                return redirect(url_for('index'))

        # Salvar os documentos no S3
        documento_frente_url = None
        documento_verso_url = None
        documento_rosto_url = None

        if documento_frente and documento_verso and documento_rosto:
            documento_frente_filename = secure_filename(documento_frente.filename)
            documento_verso_filename = secure_filename(documento_verso.filename)
            documento_rosto_filename = secure_filename(documento_rosto.filename)

            # Validar documentos
            for doc, filename in [(documento_frente, documento_frente_filename),
                                  (documento_verso, documento_verso_filename),
                                  (documento_rosto, documento_rosto_filename)]:
                if not is_safe_file(doc, ALLOWED_IMAGE_EXTENSIONS):
                    flash_with_timeout(f"Formato do documento ({filename}) inválido ou arquivo corrompido.", 'error')
                    return redirect(url_for('index'))

            # Upload dos documentos
            documento_frente_url = upload_to_s3(documento_frente, f"documentos/{documento_frente_filename}")
            documento_verso_url = upload_to_s3(documento_verso, f"documentos/{documento_verso_filename}")
            documento_rosto_url = upload_to_s3(documento_rosto, f"documentos/{documento_rosto_filename}")

            if not (documento_frente_url and documento_verso_url and documento_rosto_url):
                flash_with_timeout("Erro ao fazer upload dos documentos.", 'error')
                return redirect(url_for('index'))

        # Inserir no banco de dados
        cursor.execute(
            "INSERT INTO usuarios (nome_usuario, email, senha, tipo_usuario, status, codigo_verificacao, documento_frente_url, documento_verso_url, documento_rosto_url, cpf) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (username, email, hashed_password, 'criador', 'nao_verificado', verification_code, documento_frente_url, documento_verso_url, documento_rosto_url, cpf)
        )
        conn.commit()

        # Obter o ID do usuário recém-criado
        user_id = cursor.lastrowid

        # Inserir informações do perfil do criador
        cursor.execute(
            "INSERT INTO perfis_criadores (usuario_id, display_name, profile_picture_url, cover_photo_url) VALUES (%s, %s, %s, %s)",
            (user_id, username, profile_picture_url, cover_photo_url)
        )
        conn.commit()

        # Enviar e-mail de verificação
        msg = Message('Verificação de E-mail', recipients=[email])
        msg.body = f'Seu código de verificação é: {verification_code}'
        mail.send(msg)

        # Armazenar o e-mail na sessão para ser usado na página de verificação
        session['user_email'] = email
        session['verification_pending'] = True
        
        flash_with_timeout("Cadastro realizado como criador! Verifique seu e-mail para concluir.", 'success')

    except mysql.connector.IntegrityError:
        flash_with_timeout("Email já cadastrado.", 'error')
    except Exception as e:
        flash_with_timeout(f"Ocorreu um erro: {str(e)}", 'error')

    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()  # Remove tudo da sessão
    flash_with_timeout("Você saiu da conta.", 'info')
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    email = sanitize_input(request.form['recovery-email'])

    if not is_valid_email(email):
        flash_with_timeout("E-mail inválido.", 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    
    if not user:
        flash_with_timeout("E-mail não encontrado.", 'error')
        return redirect(url_for('index'))

    # Gerar e enviar código de recuperação
    recovery_code = generate_verification_code()
    cursor.execute("UPDATE usuarios SET codigo_verificacao = %s WHERE email = %s", (recovery_code, email))
    conn.commit()

    # Log para verificar o email e o código de recuperação
    print(f"Email: {email}, Código de Verificação: {recovery_code}")

    try:
        msg = Message('Recuperação de Senha', recipients=[email])
        msg.body = f'Seu código de recuperação é: {recovery_code}'
        mail.send(msg)
        flash_with_timeout("Código de recuperação enviado ao e-mail.", 'success')
    except Exception as e:
        flash_with_timeout(f"Erro ao enviar o e-mail: {str(e)}", 'error')

    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/reset_password/<email>', methods=['POST'])
def reset_password(email):
    code = request.form['verification-code']
    new_password = request.form['new-password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT codigo_verificacao FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    # Log para verificar o código inserido e o código armazenado
    if user:
        print(f"Código inserido: {code}, Código armazenado: {user[0]}")
    else:
        print(f"Nenhum usuário encontrado para o email: {email}")

    if not user or user[0] != code:
        flash_with_timeout("Código de recuperação inválido.", 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('index'))

    hashed_password = generate_password_hash(new_password)
    
    # Log para verificar a atualização da senha
    print(f"Atualizando a senha para o email: {email}")

    cursor.execute("UPDATE usuarios SET senha = %s, codigo_verificacao = NULL WHERE email = %s",
                   (hashed_password, email))
    
    # Log para verificar se a atualização foi bem-sucedida
    if cursor.rowcount == 0:
        print("Nenhuma linha foi atualizada. Verifique se o email está correto.")
    else:
        print("Senha atualizada com sucesso.")

    conn.commit()
    flash_with_timeout("Senha redefinida com sucesso!", 'success')
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/upload_free_media', methods=['POST'])
def upload_free_media():
    if 'username' not in session:
        flash("Você precisa estar logado para enviar mídia.", 'error')
        return redirect(url_for('index'))

    categoria = request.form.get('categoria')
    media_file = request.files.get('media')
    media_title = sanitize_input(request.form.get('media_title'))
    media_description = sanitize_input(request.form.get('media_description'))
    participantes = sanitize_input(request.form.get('participantes'))  # Captura os participantes

    if not categoria or not media_file:
        flash("Categoria e arquivo são obrigatórios.", 'error')
        return redirect(url_for('edit_profile'))

    # Validação de tipo de arquivo (USANDO A FUNÇÃO ATUALIZADA)
    filename = secure_filename(media_file.filename)

    # Determina o tipo de arquivo permitido com base na extensão
    if filename.lower().endswith(tuple(ALLOWED_IMAGE_EXTENSIONS)):
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS
        max_size = MAX_IMAGE_SIZE
    elif filename.lower().endswith(tuple(ALLOWED_VIDEO_EXTENSIONS)):
        allowed_extensions = ALLOWED_VIDEO_EXTENSIONS
        max_size = MAX_VIDEO_SIZE
    else:
        flash("Formato de arquivo inválido. Permitido: imagens (PNG, JPG, GIF) e vídeos (MP4, MOV, AVI).", 'error')
        return redirect(url_for('edit_profile'))

    # Verifica se o arquivo é seguro (extensão, tipo MIME e tamanho)
    if not is_safe_file(media_file, allowed_extensions):
        flash("Formato de arquivo inválido ou tipo de conteúdo não corresponde.", 'error')
        return redirect(url_for('edit_profile'))

    # Verificação de tamanho
    media_file.seek(0, 2)  # Move o ponteiro para o final do arquivo
    file_size = media_file.tell()  # Obtém o tamanho do arquivo
    media_file.seek(0)  # Reset file pointer

    if file_size > max_size:
        flash(f"Arquivo muito grande. Máximo {max_size / (1024 * 1024)}MB permitido.", 'error')
        return redirect(url_for('edit_profile'))

    # Fazer upload do arquivo para o S3
    media_url = upload_to_s3(media_file, f"media/{filename}")
    if not media_url:
        flash("Erro ao fazer upload da mídia.", 'error')
        return redirect(url_for('edit_profile'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (session['username'],))
    user_id = cursor.fetchone()[0]

    # Determinar o tipo baseado na extensão
    file_type = 'video' if filename.lower().endswith(tuple(ALLOWED_VIDEO_EXTENSIONS)) else 'image'

    # Inserir na tabela media com status 'pendente'
    cursor.execute("""
    INSERT INTO media (usuario_id, filename, type, status, categoria, title, description, is_free)
    VALUES (%s, %s, %s, 'pendente', %s, %s, %s, TRUE)
    """, (
        user_id,
        media_url,  # Agora salvamos a URL completa no banco de dados
        file_type,
        categoria,
        media_title,
        media_description
    ))

    media_id = cursor.lastrowid

    # Processar participantes
    if participantes:
        nomes = [sanitize_input(nome.strip()) for nome in participantes.split(',') if nome.strip()]
        for nome in nomes:
            cursor.execute(
                "INSERT INTO midia_pessoas (midia_id, nome_pessoa) VALUES (%s, %s)",
                (media_id, nome)
            )

    socketio.emit("nova_midia_admin", {
        "usuario_id": user_id,
        "mensagem": f"📥 Nova mídia enviada por @{session['username']}. Aguardando aprovação.",
        "midia": {
            "id": media_id,
            "filename": media_url,  # Usamos a URL completa aqui
            "type": file_type,
            "categoria": categoria,
            "descricao": media_description,
            "participantes": nomes if 'nomes' in locals() else []  # Adiciona os participantes
        }
    })

    conn.commit()
    cursor.close()
    conn.close()

    flash("Mídia enviada com sucesso! Aguardando aprovação.", 'success')
    return redirect(url_for('profile'))

@app.route('/upload_trailer', methods=['POST'])
def upload_trailer():
    if 'username' not in session:
        flash("Você precisa estar logado para enviar um trailer.", 'error')
        return redirect(url_for('index'))

    video_title = sanitize_input(request.form.get('video_title'))
    video_description = sanitize_input(request.form.get('video_description'))
    video_file = request.files.get('video_file')
    profile_picture = request.files.get('profile_picture')
    participantes = sanitize_input(request.form.get('participantes'))  # Captura os participantes

    if not video_title or not video_file:
        flash("Título e arquivo de vídeo são obrigatórios.", 'error')
        return redirect(url_for('index'))

    # Validação do arquivo de vídeo (USANDO A FUNÇÃO ATUALIZADA)
    video_filename = secure_filename(video_file.filename)

    if not is_safe_file(video_file, ALLOWED_VIDEO_EXTENSIONS):
        flash("Formato de vídeo inválido ou tipo de conteúdo não corresponde. Permitido: MP4, MOV, AVI.", 'error')
        return redirect(url_for('index'))

    # Verificação de tamanho
    video_file.seek(0, 2)  # Move o ponteiro para o final do arquivo
    file_size = video_file.tell()  # Obtém o tamanho do arquivo
    video_file.seek(0)  # Reset file pointer

    if file_size > MAX_VIDEO_SIZE:
        flash(f"Vídeo muito grande. Máximo {MAX_VIDEO_SIZE / (1024 * 1024)}MB permitido.", 'error')
        return redirect(url_for('index'))

    # Fazer upload do trailer para o S3
    video_url = upload_to_s3(video_file, f"trailers/{video_filename}")
    if not video_url:
        flash("Erro ao fazer upload do trailer.", 'error')
        return redirect(url_for('index'))

    # Fazer upload da imagem de perfil para o S3, se fornecida
    profile_picture_url = None
    if profile_picture:
        profile_picture_filename = secure_filename(profile_picture.filename)

        if not is_safe_file(profile_picture, ALLOWED_IMAGE_EXTENSIONS):
            flash("Formato de imagem de perfil inválido ou tipo de conteúdo não corresponde. Permitido: PNG, JPG, GIF.", 'error')
            return redirect(url_for('index'))

        # Verificação de tamanho
        profile_picture.seek(0, 2)  # Move o ponteiro para o final do arquivo
        profile_picture_size = profile_picture.tell()
        profile_picture.seek(0)  # Reset file pointer

        if profile_picture_size > MAX_IMAGE_SIZE:
            flash("Imagem de perfil muito grande. Máximo 10MB permitido.", 'error')
            return redirect(url_for('index'))

        profile_picture_url = upload_to_s3(profile_picture, f"profile_pictures/{profile_picture_filename}")
        if not profile_picture_url:
            flash("Erro ao fazer upload da imagem de perfil.", 'error')
            return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (session['username'],))
    user_id = cursor.fetchone()[0]

    # Inserir na tabela media com status 'pendente' e categoria 'trailer'
    cursor.execute("""
    INSERT INTO media (usuario_id, filename, type, status, categoria, title, description, is_free)
    VALUES (%s, %s, 'video', 'pendente', 'trailer', %s, %s, FALSE)
    """, (user_id, video_url, video_title, video_description))

    media_id = cursor.lastrowid

    # Processar participantes
    if participantes:
        nomes = [sanitize_input(nome.strip()) for nome in participantes.split(',') if nome.strip()]
        for nome in nomes:
            cursor.execute(
                "INSERT INTO midia_pessoas (midia_id, nome_pessoa) VALUES (%s, %s)",
                (media_id, nome)
            )

    socketio.emit("nova_midia_admin", {
        "usuario_id": user_id,
        "mensagem": f"📥 Novo trailer enviado por @{session['username']}. Aguardando aprovação.",
        "midia": {
            "id": media_id,
            "filename": video_url,  # Usamos a URL completa aqui
            "type": "video",
            "categoria": "trailer",
            "descricao": video_description,
            "participantes": nomes if 'nomes' in locals() else []  # Adiciona os participantes
        }
    })

    # Atualizar a tabela perfis_criadores com a URL da imagem de perfil
    if profile_picture_url:
        cursor.execute("""
        UPDATE perfis_criadores 
        SET profile_picture_url = %s 
        WHERE usuario_id = %s
        """, (profile_picture_url, user_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Mídia enviada com sucesso! Aguardando aprovação.", 'success')
    return redirect(url_for('profile'))

@app.route('/increment_views/<int:media_id>', methods=['POST'])
def increment_views(media_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Incrementar o contador de visualizações
        cursor.execute("UPDATE media SET views = views + 1 WHERE id = %s", (media_id,))
        conn.commit()

        cursor.close()
        conn.close()
        return '', 204  # Retorna sem conteúdo para o front-end
    except Exception as e:
        print(f"Erro ao incrementar visualizações: {e}")
        return jsonify({'error': 'Erro ao incrementar visualizações'}), 500

@app.route('/admin/hidden_access', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = sanitize_input(request.form['username'])
        password = sanitize_input(request.form['password'])

        # Conectar ao banco de dados e verificar se o usuário é um administrador
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT senha FROM usuarios WHERE nome_usuario = %s AND tipo_usuario = 'admin'", (username,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin and check_password_hash(admin[0], password):  # Verifica a senha
            session['admin_logged_in'] = True  # Define a sessão para o administrador
            flash("Login bem-sucedido!", 'success')
            return redirect(url_for('verificar_usuarios'))  # Redireciona para a página de verificação
        else:
            flash("Nome de usuário ou senha inválidos.", 'error')

    return render_template('admin_login.html')  # Renderiza a página de login

@app.route('/admin/verificar_usuarios')
def verificar_usuarios():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔹 Buscar criadores de conteúdo
    cursor.execute("""
        SELECT u.id, u.nome_usuario, u.documento_frente_url, u.documento_verso_url, u.cpf, 
               u.documento_rosto_url, u.status_verificacao, p.valor_assinatura
        FROM usuarios u
        LEFT JOIN perfis_criadores p ON u.id = p.usuario_id
        WHERE u.status_verificacao IN ('verificado', 'pendente') AND u.tipo_usuario = 'criador'
    """)
    criadores = cursor.fetchall()

    # Função auxiliar para verificar se uma URL já está completa
    def is_complete_url(url):
        return url and (url.startswith("http://") or url.startswith("https://"))

    # 🔹 Converter URLs locais para URLs do S3
    bucket_url = f"https://{os.getenv('AWS_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com"

    criadores_com_urls = []
    for criador in criadores:
        usuario_id, nome_usuario, documento_frente_url, documento_verso_url, cpf, \
            documento_rosto_url, status_verificacao, valor_assinatura = criador

        # Convertendo URLs locais para URLs do S3 (somente se não forem URLs completas)
        documento_frente_url = documento_frente_url if is_complete_url(documento_frente_url) else \
            f"{bucket_url}/documents/{documento_frente_url}" if documento_frente_url else None

        documento_verso_url = documento_verso_url if is_complete_url(documento_verso_url) else \
            f"{bucket_url}/documents/{documento_verso_url}" if documento_verso_url else None

        documento_rosto_url = documento_rosto_url if is_complete_url(documento_rosto_url) else \
            f"{bucket_url}/documents/{documento_rosto_url}" if documento_rosto_url else None

        criadores_com_urls.append((
            usuario_id, nome_usuario, documento_frente_url, documento_verso_url, cpf,
            documento_rosto_url, status_verificacao, valor_assinatura
        ))

    # 🔹 Buscar mídias pendentes para cada criador
    videos_pendentes = []
    for criador in criadores_com_urls:
        usuario_id = criador[0]
        cursor.execute("""
            SELECT 
                m.id, m.filename, m.type, m.status, m.categoria, m.description,
                (SELECT GROUP_CONCAT(mp.nome_pessoa SEPARATOR '|||') 
                FROM midia_pessoas mp 
                WHERE mp.midia_id = m.id) AS pessoas_marcadas
            FROM media m
            WHERE m.usuario_id = %s AND m.status IN ('pendente', 'disponivel', 'bloqueado', 'excluido')
        """, (usuario_id,))

        # Processa os vídeos e transforma os nomes em lista
        videos = []
        for v in cursor.fetchall():
            video_url = v[1] if is_complete_url(v[1]) else f"{bucket_url}/media/{v[1]}"  # Convertendo para URL do S3
            videos.append((
                v[0], video_url, v[2], v[3], v[4], v[5],  # dados da mídia
                v[6].split('|||') if v[6] else []   # lista de nomes
            ))

        videos_pendentes.append((usuario_id, videos))

    # 🔹 Buscar informações de assinaturas, vendas de vídeos e histórico de acertos
    criadores_com_dados = []
    for criador in criadores_com_urls:
        usuario_id, nome_usuario, documento_frente_url, documento_verso_url, cpf, \
            documento_rosto_url, status_verificacao, valor_assinatura = criador

        # 📌 Buscar número de assinaturas ativas (considerando validade)
        cursor.execute("""
            SELECT COUNT(*)
            FROM assinaturas
            WHERE criador_assinado = %s
              AND status = 'ativo'
              AND CURDATE() BETWEEN data_inicio AND data_fim
        """, (nome_usuario,))
        active_subscriptions = cursor.fetchone()[0]

        # 📌 Buscar faturamento do mês atual (assinaturas + vídeos vendidos)
        from datetime import datetime
        mes_atual = datetime.now().strftime("%Y-%m")

        cursor.execute("""
            SELECT COUNT(*), COALESCE(SUM(valor_pago), 0) 
            FROM assinaturas 
            WHERE criador_assinado = %s AND status = 'ativo'
            AND DATE(data_inicio) >= %s AND DATE(data_inicio) <= LAST_DAY(%s)
        """, (nome_usuario, mes_atual + '-01', mes_atual + '-01'))
        subscription_info = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(vc.id), COALESCE(SUM(m.valor_video), 0)
            FROM videos_comprados vc
            JOIN media m ON vc.media_id = m.id
            WHERE m.usuario_id = %s
            AND vc.mes_ano = %s
        """, (usuario_id, mes_atual))
        video_sales_info = cursor.fetchone()

        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1)
        mes_anterior = (primeiro_dia_mes - timedelta(days=1)).strftime("%Y-%m")

        cursor.execute("""
            SELECT id, mes_ano, total_assinaturas, total_videos, status
            FROM acertos_mensais
            WHERE usuario_id = %s AND mes_ano = %s
            LIMIT 1
        """, (usuario_id, mes_anterior))
        acerto_historico = cursor.fetchall()

        # 📌 Calcular faturamento total e saldo líquido (75%)
        faturamento_total = Decimal(str(subscription_info[1])) + Decimal(str(video_sales_info[1]))
        saldo_liquido = (faturamento_total * Decimal('0.75')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # 📌 Criador com todas as informações
        criador_completo = (
            usuario_id, nome_usuario, documento_frente_url, documento_verso_url, cpf, documento_rosto_url,
            status_verificacao, valor_assinatura, subscription_info[0], subscription_info[1],
            video_sales_info[0], video_sales_info[1], acerto_historico, saldo_liquido, active_subscriptions
        )
        criadores_com_dados.append(criador_completo)

    cursor.close()
    conn.close()

    return render_template(
        'verificar_usuarios.html', 
        usuarios=criadores_com_dados, 
        videos=videos_pendentes
    )

@app.route('/admin/gerar_acertos', methods=['POST'])
def gerar_acertos():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        from datetime import datetime, timedelta
        hoje = datetime.now()
        primeiro_dia_mes_atual = hoje.replace(day=1)
        mes_anterior = (primeiro_dia_mes_atual - timedelta(days=1)).strftime("%Y-%m")

        # 🔍 Buscar criadores verificados
        cursor.execute("""
            SELECT id, nome_usuario 
            FROM usuarios 
            WHERE tipo_usuario = 'criador' AND status_verificacao = 'verificado'
        """)
        criadores = cursor.fetchall()

        for criador_id, criador_assinado in criadores:
            # ✅ Verifica se já existe acerto deste criador para o mês anterior
            cursor.execute("""
                SELECT id FROM acertos_mensais 
                WHERE usuario_id = %s AND criador_assinado = %s AND mes_ano = %s
            """, (criador_id, criador_assinado, mes_anterior))
            if cursor.fetchone():
                continue  # Já existe, pula

            # 🔸 Assinaturas do mês anterior
            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(valor_pago), 0) 
                FROM assinaturas 
                WHERE criador_assinado = %s 
                AND status = 'ativo' 
                AND mes_ano = %s
            """, (criador_assinado, mes_anterior))
            total_assinantes, total_assinaturas = cursor.fetchone()

            # 🔸 Vídeos vendidos no mês anterior (pendentes)
            cursor.execute("""
                SELECT COUNT(vc.id), COALESCE(SUM(m.valor_video), 0)
                FROM videos_comprados vc
                JOIN media m ON vc.media_id = m.id
                WHERE m.usuario_id = %s
                AND vc.mes_ano = %s
                AND vc.status = 'pendente'
            """, (criador_id, mes_anterior))
            total_videos, valor_videos = cursor.fetchone()

            # ✅ Inserir acerto
            cursor.execute("""
                INSERT INTO acertos_mensais (
                    usuario_id, criador_assinado, 
                    total_assinaturas, total_videos, 
                    mes_ano, status
                ) VALUES (%s, %s, %s, %s, %s, 'pago')
            """, (criador_id, criador_assinado, total_assinaturas, valor_videos, mes_anterior))

            # 🧹 Marcar vídeos como pagos (apenas do mês anterior)
            cursor.execute("""
                UPDATE videos_comprados
                SET status = 'pago'
                WHERE media_id IN (SELECT id FROM media WHERE usuario_id = %s)
                AND mes_ano = %s
                AND status = 'pendente'
            """, (criador_id, mes_anterior))

            # 💤 Inativar assinaturas expiradas
            cursor.execute("""
                UPDATE assinaturas
                SET status = 'inativo'
                WHERE criador_assinado = %s 
                AND status = 'ativo'
                AND data_fim < NOW()
            """, (criador_assinado,))

        conn.commit()
        flash("Acertos gerados com sucesso para o mês anterior!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Erro ao gerar acertos: {e}", "error")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('verificar_usuarios'))


@app.route('/admin/verificar_criadores')
def verificar_criadores():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nome_usuario, documento_frente_url, documento_verso_url 
        FROM usuarios 
        WHERE status = 'pendente' AND tipo_usuario = 'criador'
    """)
    criadores_pendentes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('verificar_usuarios.html', usuarios=criadores_pendentes)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)  # Remove a sessão do administrador
    flash("Você saiu da conta de administrador.", 'info')
    return redirect(url_for('index'))  # Redireciona para a página inicial

@app.route('/admin/liberar_usuario/<int:user_id>', methods=['POST'])
def liberar_usuario(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Primeiro atualiza o status
        cursor.execute("UPDATE usuarios SET status_verificacao = 'verificado' WHERE id = %s", (user_id,))
        conn.commit()
        
        # Depois busca o nome do usuário em uma consulta separada
        cursor.execute("SELECT nome_usuario FROM usuarios WHERE id = %s", (user_id,))
        updated_user = cursor.fetchone()
        
        message = f"Usuário {updated_user[0]} liberado com sucesso!" if updated_user else "Usuário liberado com sucesso!"
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=True, message=message, username=updated_user[0] if updated_user else None)
        
        flash(message, 'success')
    except Exception as e:
        error = f"Erro ao liberar usuário: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error=error)
        flash(error, 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('verificar_usuarios'))

@app.route('/admin/excluir_usuario/<int:user_id>', methods=['POST'])
def excluir_usuario(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Remove todas as mídias do usuário (com tratamento de dependências)
        cursor.execute("SELECT id FROM media WHERE usuario_id = %s", (user_id,))
        media_ids = [row[0] for row in cursor.fetchall()]

        for media_id in media_ids:
            # Remove referências em `videos_comprados`
            cursor.execute("DELETE FROM videos_comprados WHERE media_id = %s", (media_id,))
            
            # Remove referências em `midia_pessoas`
            cursor.execute("DELETE FROM midia_pessoas WHERE midia_id = %s", (media_id,))
            
            # Verifica se o arquivo pode ser excluído (se não for usado por outros)
            cursor.execute("SELECT filename FROM media WHERE id = %s", (media_id,))
            filename = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM media WHERE filename = %s AND id != %s", (filename, media_id))
            count = cursor.fetchone()[0]
            
            if count == 0:  # Se ninguém mais usa o arquivo, exclui
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'media', filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Exclui a mídia
            cursor.execute("DELETE FROM media WHERE id = %s", (media_id,))

        # 2. Remove registros de curtidas
        cursor.execute("DELETE FROM curtidas WHERE usuario_id = %s OR criador_id = %s", (user_id, user_id))
        
        # 3. Remove registros de seguidores
        cursor.execute("DELETE FROM seguidores WHERE usuario_id = %s OR criador_id = %s", (user_id, user_id))
        
        # 4. Remove mensagens - AGORA EXCLUINDO FISICAMENTE
        cursor.execute("DELETE FROM mensagens WHERE remetente_id = %s OR destinatario_id = %s", (user_id, user_id))
        
        # 5. Remove perfil de criador (se existir)
        cursor.execute("DELETE FROM perfis_criadores WHERE usuario_id = %s", (user_id,))
        
        # 6. Remove assinaturas vinculadas
        cursor.execute("DELETE FROM assinaturas WHERE usuario_id = %s OR criador_assinado = (SELECT nome_usuario FROM usuarios WHERE id = %s)", (user_id, user_id))
        
        # 7. Remove acertos mensais
        cursor.execute("DELETE FROM acertos_mensais WHERE usuario_id = %s", (user_id,))
        
        # 8. Finalmente, exclui o usuário
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
        conn.commit()
        
        message = "Usuário excluído com sucesso!"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=True, message=message)
        flash(message, 'success')
        
    except Exception as e:
        conn.rollback()
        error = f"Erro ao excluir o usuário: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error=error)
        flash(error, 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('verificar_usuarios'))

@app.route('/admin/aprovar_media/<int:media_id>', methods=['POST'])
def aprovar_media(media_id):
    if not session.get('admin_logged_in'):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'unauthorized'}), 403
        flash("Acesso negado.", 'error')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT categoria FROM media WHERE id = %s", (media_id,))
        media = cursor.fetchone()

        if media:
            cursor.execute("""
                UPDATE media 
                SET status = 'disponivel' 
                WHERE id = %s
            """, (media_id,))
            conn.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True})

            flash("Mídia aprovada com sucesso!", 'success')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'not_found'}), 404
            flash("Mídia não encontrada.", 'error')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': str(e)}), 500
        flash(f"Erro ao aprovar a mídia: {str(e)}", 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('verificar_usuarios'))
 
@app.route('/admin/delete_media/<int:media_id>', methods=['POST'])
def admin_delete_media(media_id):
    if not session.get('admin_logged_in'):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=False, error="Acesso negado"), 403
        flash("Acesso negado.", 'error')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT status FROM media WHERE id = %s", (media_id,))
        media = cursor.fetchone()

        if not media:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(success=False, error="Mídia não encontrada")
            flash("Nenhuma mídia encontrada com esse ID.", 'error')
            return redirect(url_for('verificar_usuarios'))

        cursor.execute("""
            UPDATE media 
            SET status = 'excluido', mensagem = 'Esta mídia foi excluída pelo administrador. Entre em contato com o suporte para esclarecimentos.'
            WHERE id = %s
        """, (media_id,))
        conn.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=True)

        flash("Mídia excluída com sucesso.", 'success')
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=False, error=str(e))
        flash(f"Erro ao excluir: {str(e)}", 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('verificar_usuarios'))

@app.route('/admin/block_media/<int:media_id>', methods=['POST'])
def admin_block_media(media_id):
    if not session.get('admin_logged_in'):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=False, error="Acesso negado"), 403
        flash("Acesso negado.", 'error')
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT status FROM media WHERE id = %s", (media_id,))
        current_status = cursor.fetchone()

        if not current_status:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(success=False, error="Mídia não encontrada")
            flash("Mídia não encontrada.", 'error')
            return redirect(url_for('verificar_usuarios'))

        if current_status[0] == 'bloqueado':
            new_status = 'disponivel'
            message = None
        else:
            new_status = 'bloqueado'
            message = 'Esta mídia foi bloqueada pelo administrador.'

        cursor.execute("""
            UPDATE media 
            SET status = %s, mensagem = %s WHERE id = %s
        """, (new_status, message, media_id))
        conn.commit()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=True, status=new_status)

        flash(f"Mídia {'bloqueada' if new_status == 'bloqueado' else 'desbloqueada'} com sucesso.", 'success')
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(success=False, error=str(e))
        flash(f"Erro: {str(e)}", 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('verificar_usuarios'))

@app.route('/search', methods=['GET'])
def search_videos():
    search_term = request.args.get('q', '').lower().strip()
    search_term = sanitize_input(search_term)  # 🛡️ Proteção contra injeção

    if not search_term:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            m.id, 
            m.title, 
            m.description, 
            m.filename, 
            m.views,
            p.profile_picture_url
        FROM media AS m
        LEFT JOIN perfis_criadores AS p ON m.usuario_id = p.usuario_id
        WHERE m.type = 'video' 
        AND m.status = 'disponivel' 
        AND (LOWER(m.title) LIKE %s OR LOWER(m.description) LIKE %s)
        AND m.categoria IN ('anal', 'boquete', 'casal', 'novinha', 'orgia', 'solo', 'suruba', 'trisal')
    """

    like_term = f"%{search_term}%"
    cursor.execute(query, (like_term, like_term))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(results)

@app.route('/update_subscription_price', methods=['POST'])
def update_subscription_price():
    if 'username' not in session:
        flash("Você precisa estar logado para atualizar o valor da assinatura.", 'error')
        return redirect(url_for('index'))

    valor_assinatura = request.form.get('valor_assinatura')
    if not valor_assinatura:
        flash("Valor da assinatura é obrigatório.", 'error')
        return redirect(url_for('profile'))

    # Converta o valor para float
    try:
        valor_assinatura = float(valor_assinatura)
    except ValueError:
        flash("Valor da assinatura inválido.", 'error')
        return redirect(url_for('profile'))

    # Verifique se o valor é maior ou igual a 19.90
    if valor_assinatura < 19.90:
        flash("O valor mínimo da assinatura é R$ 19,90.", 'error')
        return redirect(url_for('profile'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE perfis_criadores 
            SET valor_assinatura = %s 
            WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (valor_assinatura, session['username']))
        conn.commit()
        flash("Valor da assinatura atualizado com sucesso!", 'success')
    except Exception as e:
        flash(f"Erro ao atualizar o valor da assinatura: {str(e)}", 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('profile'))

@app.route("/process_payment_pix", methods=["POST"])
def process_payment_pix():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Usuário não autenticado"}), 403

    try:
        data = request.get_json()
        creator_username = sanitize_input(data.get("creator_username", "")).strip()
        media_id = data.get("media_id")  # ID do vídeo (opcional)
        tipo_pagamento = sanitize_input(data.get("tipo_pagamento", "assinatura"))

        if not creator_username:
            return jsonify({"error": "Criador de conteúdo não especificado"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Buscar dados do usuário autenticado, incluindo CPF
        cursor.execute("SELECT nome_usuario, email, cpf FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        nome_usuario, email, cpf = user

        # Sanitize CPF (remove pontuações, só dígitos)
        cpf = re.sub(r"\D", "", cpf or "")
        if not cpf or len(cpf) != 11:
            return jsonify({"error": "CPF inválido ou ausente"}), 400

        # Determina valor a pagar e ID do criador
        if media_id:
            cursor.execute("SELECT valor_video, usuario_id FROM media WHERE id = %s", (media_id,))
            video_info = cursor.fetchone()
            if not video_info:
                return jsonify({"error": "Vídeo não encontrado"}), 404
            transaction_amount, criador_id = map(float, video_info)
        else:
            cursor.execute("""
                SELECT valor_assinatura, usuario_id 
                FROM perfis_criadores 
                WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
            """, (creator_username,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"error": "Assinatura não encontrada para este criador."}), 404
            transaction_amount, criador_id = map(float, result)

        mes_ano_atual = datetime.now().strftime('%Y-%m')

        # Criar pagamento Pix no MercadoPago
        payment_data = {
            "transaction_amount": transaction_amount,
            "description": f"{tipo_pagamento}:{media_id or ''}",
            "payment_method_id": "pix",
            "payer": {
                "email": email,
                "first_name": nome_usuario,
                "last_name": "",
                "identification": {
                    "type": "CPF",
                    "number": cpf
                }
            },
            "external_reference": str(criador_id)
        }

        payment = sdk.payment().create(payment_data)
        response = payment.get("response", {})

        if response.get("status") in ["pending", "approved"]:
            qr_code_base64 = response["point_of_interaction"]["transaction_data"]["qr_code_base64"]
            qr_code = response["point_of_interaction"]["transaction_data"]["qr_code"]
            transaction_id = response.get("id")

            # Registrar pagamento como pendente
            cursor.execute("""
                INSERT INTO pagamentos_pix (usuario_id, criador_assinado, media_id, tipo_pagamento, 
                                            transaction_id, valor_pago, status, mes_ano)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                creator_username,
                media_id,
                tipo_pagamento,
                transaction_id,
                transaction_amount,
                response["status"],
                mes_ano_atual
            ))
            conn.commit()

            return jsonify({
                "status": "pending",
                "qr_code": qr_code_base64,
                "qr_code_copy": qr_code,
                "transaction_id": transaction_id,
                "mes_ano": mes_ano_atual
            })

        logger.warning(f"Falha no pagamento Pix: {response}")
        return jsonify({"error": "Erro ao criar pagamento Pix"}), 400

    except Exception as e:
        logger.exception("Erro inesperado no processamento Pix")
        return jsonify({"error": "Erro interno"}), 500

    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/get_user_info", methods=["GET"])
def get_user_info():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Usuário não autenticado"}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT nome_usuario, email FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        nome_usuario, email = user
        return jsonify({
            "success": True,
            "email": email,
            "username": nome_usuario
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/process_payment", methods=["POST"])
def create_card_payment():
    """Cria um pagamento via cartão"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Usuário não autenticado"}), 403

    data = request.json
    print("Dados recebidos:", data)

    creator_username = sanitize_input(data.get("creator_username"))
    media_id = data.get("media_id")
    tipo_pagamento = sanitize_input(data.get("tipo_pagamento", "assinatura"))
    print("Tipo de Pagamento recebido:", tipo_pagamento)

    if not creator_username:
        return jsonify({"error": "Criador de conteúdo não especificado"}), 400

    conn = get_db_connection()
    
    try:
        # 🛑 Verifica se o usuário já tem uma assinatura ativa (apenas para assinaturas)
        if not media_id:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, status, data_fim 
                    FROM assinaturas 
                    WHERE usuario_id = %s 
                    AND criador_assinado = %s 
                    AND status = 'ativo'
                    AND CURDATE() BETWEEN data_inicio AND data_fim
                """, (user_id, creator_username))

                active_subscription = cursor.fetchone()
                cursor.fetchall()  # 🔥 Limpa qualquer resultado pendente

            if active_subscription:
                data_fim = active_subscription[2]
                print(f"Erro: Assinatura ativa encontrada até {data_fim}")
                return jsonify({
                    "error": f"Você já tem uma assinatura ativa para este criador. A assinatura expira em {data_fim}."
                }), 400

        # 🛑 Buscar e-mail do usuário logado
        with conn.cursor() as cursor:
            cursor.execute("SELECT nome_usuario, email FROM usuarios WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            cursor.fetchall()

        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        nome_usuario, email = user

        # 🛑 Determina o valor do pagamento
        if media_id:
            with conn.cursor() as cursor:
                # Busca o valor do vídeo e o criador_id (usuario_id do criador)
                cursor.execute("""
                    SELECT valor_video, usuario_id 
                    FROM media 
                    WHERE id = %s
                """, (media_id,))
                video_info = cursor.fetchone()
                cursor.fetchall()
            
            if not video_info:
                return jsonify({"error": "Vídeo não encontrado ou sem valor definido."}), 404
            
            valor_video, criador_id = video_info
            transaction_amount = float(valor_video)
        else:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT valor_assinatura 
                    FROM perfis_criadores 
                    WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
                """, (creator_username,))
                valor_assinatura = cursor.fetchone()
                cursor.fetchall()
            
            if not valor_assinatura:
                return jsonify({"error": "Valor da assinatura não encontrado para o criador."}), 404
            transaction_amount = float(valor_assinatura[0])

        required_fields = ["token", "payment_method_id", "installments", "issuer_id"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Campo obrigatório ausente: {field}"}), 400

        payment_data = {
            "transaction_amount": transaction_amount,
            "token": data["token"],
            "description": "Pagamento Premium",
            "payment_method_id": data["payment_method_id"],
            "installments": int(data["installments"]),
            "issuer_id": data["issuer_id"],
            "payer": {"email": email}
        }

        print("Enviando pagamento para Mercado Pago:", payment_data)
        payment = sdk.payment().create(payment_data)
        response = payment["response"]

        if response.get("status") in ["approved", "pending", "in_process"]:
            transaction_id = response["id"]
            mes_ano_atual = datetime.now().strftime('%Y-%m')  # Obtém "YYYY-MM"

            with conn.cursor() as cursor:
                if media_id:
                    # 🟢 Pagamento de vídeo (adiciona na tabela `videos_comprados`)
                    cursor.execute("""
                        INSERT INTO videos_comprados (usuario_id, media_id, transaction_id, mes_ano, criador_id, status)
                        VALUES (%s, %s, %s, %s, %s, 'pendente')
                    """, (user_id, media_id, transaction_id, mes_ano_atual, criador_id))

                    # 🔹 Atualiza ou insere no faturamento do criador (`acertos_mensais`)
                    cursor.execute("""
                        INSERT INTO acertos_mensais (usuario_id, criador_assinado, total_videos, mes_ano, status)
                        VALUES (%s, %s, %s, %s, 'pendente')
                        ON DUPLICATE KEY UPDATE total_videos = total_videos + %s
                    """, (criador_id, creator_username, transaction_amount, mes_ano_atual, transaction_amount))

                else:
                    # 🟢 Pagamento de assinatura (adiciona na tabela `assinaturas`)
                    cursor.execute("""
                        INSERT INTO assinaturas (usuario_id, criador_assinado, status, data_inicio, data_fim, transaction_id, valor_pago, tipo_pagamento, mes_ano)
                        VALUES (%s, %s, 'pendente', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY), %s, %s, 'assinatura', %s)
                        ON DUPLICATE KEY UPDATE status='pendente', data_inicio=NOW(), data_fim=DATE_ADD(NOW(), INTERVAL 30 DAY), transaction_id=%s, valor_pago=%s, tipo_pagamento='assinatura', mes_ano=%s
                    """, (user_id, creator_username, transaction_id, transaction_amount, mes_ano_atual, transaction_id, transaction_amount, mes_ano_atual))


            conn.commit()

            redirect_url = f"/dashboard/{creator_username}"
            return jsonify({
                "status": response["status"],
                "status_detail": response.get("status_detail"),
                "transaction_id": transaction_id,
                "redirect_url": redirect_url
            })
        else:
            print("⚠️ Pagamento não aprovado. Status:", response.get("status"))
            return jsonify({"error": "Pagamento não aprovado", "status": response.get("status"), "status_detail": response.get("status_detail")}), 400

    except Exception as e:
        print(f"❌ Erro ao processar pagamento: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()  # Fecha a conexão

@app.route("/mercadopago_webhook", methods=["POST"])
def mercadopago_webhook():
    try:
        data = request.get_json()
        payment_id = data.get("data", {}).get("id")

        if not payment_id:
            return jsonify({"error": "payment_id não encontrado"}), 400

        # Busca os detalhes do pagamento na API do MercadoPago
        payment_info = sdk.payment().get(payment_id)
        response = payment_info.get("response", {})

        status = response.get("status")
        if status != "approved":
            return jsonify({"error": f"Pagamento não aprovado. Status: {status}"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Verifica se o pagamento é de cartão ou Pix
            payment_method = response.get("payment_method_id")
            is_pix = payment_method == "pix"

            if is_pix:
                # Pagamento via Pix: busca os dados da transação no payload do webhook
                description = response.get("description", "")
                if "video" in description.lower():
                    tipo_pagamento = "video"
                else:
                    tipo_pagamento = "assinatura"

                usuario_id = response.get("payer", {}).get("id")
                criador_assinado = response.get("external_reference", "")
                valor_pago = float(response.get("transaction_amount", 0))
                media_id = None  # O media_id pode ser obtido do description ou external_reference, se necessário
            else:
                # Pagamento via cartão: busca os dados da transação na tabela `assinaturas`
                cursor.execute("""
                    SELECT usuario_id, tipo_pagamento, media_id, criador_assinado, valor_pago
                    FROM assinaturas 
                    WHERE transaction_id = %s
                """, (payment_id,))
                result = cursor.fetchone()

                if not result:
                    print(f"⚠️ Nenhum registro encontrado para o transaction_id: {payment_id}")
                    return jsonify({"error": "Nenhum registro encontrado para o pagamento"}), 404

                usuario_id, tipo_pagamento, media_id, criador_assinado, valor_pago = result

            if status == "approved":
                if tipo_pagamento == "assinatura":
                    # 🟢 Ativa a assinatura
                    cursor.execute("""
                        UPDATE assinaturas
                        SET status = 'ativo'
                        WHERE transaction_id = %s
                    """, (payment_id,))

                    # 🔹 Registra o faturamento da assinatura na tabela `acertos_mensais`
                    cursor.execute("""
                        INSERT INTO acertos_mensais (usuario_id, criador_assinado, total_assinaturas, mes_ano)
                        VALUES (%s, %s, %s, DATE_FORMAT(NOW(), '%Y-%m'))
                        ON DUPLICATE KEY UPDATE total_assinaturas = total_assinaturas + %s
                    """, (usuario_id, criador_assinado, valor_pago, valor_pago))

                    conn.commit()
                    print(f"🎉 Assinatura ativada para o criador {criador_assinado} pelo usuário {usuario_id}!")

                elif tipo_pagamento == "video":
                    # 🟢 Registra a compra do vídeo na tabela `videos_comprados`
                    cursor.execute("""
                        INSERT INTO videos_comprados (usuario_id, media_id, transaction_id)
                        VALUES (%s, %s, %s)
                    """, (usuario_id, media_id, payment_id))

                    # 🔹 Registra o faturamento do vídeo na tabela `acertos_mensais`
                    cursor.execute("""
                        INSERT INTO acertos_mensais (usuario_id, criador_assinado, total_videos, mes_ano)
                        VALUES (%s, %s, %s, DATE_FORMAT(NOW(), '%Y-%m'))
                        ON DUPLICATE KEY UPDATE total_videos = total_videos + %s
                    """, (usuario_id, criador_assinado, valor_pago, valor_pago))

                    conn.commit()
                    print(f"🎉 Vídeo ID {media_id} comprado pelo usuário {usuario_id}!")

        except Exception as e:
            conn.rollback()
            print(f"⚠️ Erro ao atualizar o banco de dados: {e}")
            return jsonify({"error": "Erro ao atualizar o banco de dados"}), 500
        finally:
            cursor.close()
            conn.close()

        return jsonify({"status": "processed"}), 200

    except Exception as e:
        print(f"⚠️ Erro ao processar webhook: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

@app.route('/pagamento', methods=['GET', 'POST'])
def pagamento():
    # Debug: mostra os parâmetros recebidos
    print("Parâmetros recebidos (GET):", request.args)
    print("Parâmetros recebidos (POST):", request.form)

    # Obtém os parâmetros de acordo com o método
    if request.method == 'POST':
        creator_username = request.form.get("creator")
        valor_assinatura = request.form.get("valor")
        media_id = request.form.get("media_id")
        tipo_pagamento = request.form.get("tipo_pagamento", "assinatura")
    else:
        creator_username = request.args.get("creator")
        valor_assinatura = request.args.get("valor")
        media_id = request.args.get("media_id")
        tipo_pagamento = request.args.get("tipo_pagamento", "assinatura")

    # Validação do criador (obrigatório)
    if not creator_username:
        flash("Criador de conteúdo não especificado.", 'error')
        return redirect(url_for('creators_list'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Busca o valor da assinatura no banco de dados (usando display_name)
        cursor.execute("""
            SELECT valor_assinatura 
            FROM perfis_criadores 
            WHERE display_name = %s
        """, (creator_username,))
        result = cursor.fetchone()

        print("Resultado da consulta SQL:", result)

        if not result:
            flash("Criador de conteúdo não encontrado.", 'error')
            return redirect(url_for('creators_list'))

        # Sobrescreve o valor_assinatura com o valor do banco (segurança)
        # Isso evita que um valor malicioso seja enviado pelo formulário
        valor_assinatura = float(result[0])  

    except Exception as e:
        print("Erro SQL:", str(e))
        flash(f"Erro ao buscar valor da assinatura: {str(e)}", 'error')
        return redirect(url_for('creators_list'))
    finally:
        cursor.close()
        conn.close()

    # Renderiza o template com os dados
    return render_template(
        'pagamento.html',
        username=creator_username,
        valor=valor_assinatura,
        media_id=media_id,
        tipo_pagamento=tipo_pagamento
    )

@app.route('/solicitar_saque', methods=['POST'])
def solicitar_saque():
    if 'username' not in session:
        flash("Você precisa estar logado para solicitar um saque.", 'error')
        return redirect(url_for('index'))

    user_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Buscar o saldo do criador
        cursor.execute("""
            SELECT SUM(valor_pago) as total_assinaturas, COALESCE(SUM(m.valor_video), 0) as total_videos
            FROM assinaturas a
            LEFT JOIN media m ON a.usuario_id = m.usuario_id
            WHERE a.usuario_id = %s AND a.status = 'ativo'
        """, (user_id,))
        saldo = cursor.fetchone()

        total_saldo = saldo[0] + saldo[1]

        if total_saldo <= 0:
            flash("Saldo insuficiente para saque.", 'error')
            return redirect(url_for('profile'))

        # Buscar o CPF do criador
        cursor.execute("SELECT cpf FROM usuarios WHERE id = %s", (user_id,))
        cpf = cursor.fetchone()[0]

        # Integração com o Mercado Pago para realizar o saque via Pix
        # Aqui você precisa usar a API do Mercado Pago para realizar o saque
        # Exemplo simplificado:
        # response = mercado_pago_api.solicitar_saque(cpf, total_saldo)

        # if response.status_code == 200:
        #     flash("Saque solicitado com sucesso!", 'success')
        # else:
        #     flash("Erro ao solicitar saque. Tente novamente mais tarde.", 'error')

        # Exemplo de resposta de sucesso
        flash("Saque solicitado com sucesso!", 'success')

    except Exception as e:
        print(f"Erro ao solicitar saque: {e}")
        flash("Erro ao solicitar saque. Tente novamente mais tarde.", 'error')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('profile'))

@app.route('/subscribe/<username>')
def subscribe_creator(username):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Buscar o valor da assinatura do criador
        cursor.execute("""
            SELECT valor_assinatura 
            FROM perfis_criadores 
            WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (username,))
        valor_assinatura = cursor.fetchone()

        if not valor_assinatura:
            flash("Valor da assinatura não encontrado para o criador.", 'error')
            return redirect(url_for('creators_list'))

        # Passar o valor da assinatura para o template
        return render_template('subscribe.html', username=username, valor_assinatura=valor_assinatura[0])
    except Exception as e:
        flash(f"Erro ao buscar informações do criador: {str(e)}", 'error')
        return redirect(url_for('creators_list'))
    finally:
        cursor.close()
        conn.close()

@app.route('/creators_list')
def creators_list():
    if 'user_id' not in session:  
        flash("Você precisa estar logado para assinar esse Perfil.", "error")
        return redirect(url_for("index"))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔍 Busca todas as assinaturas ativas e válidas do usuário junto com a foto do criador
    cursor.execute("""
        SELECT a.criador_assinado, a.data_inicio, a.data_fim, p.profile_picture_url 
        FROM assinaturas a
        JOIN usuarios u ON a.criador_assinado = u.nome_usuario
        JOIN perfis_criadores p ON u.id = p.usuario_id
        WHERE a.usuario_id = %s
          AND a.status = 'ativo'
          AND NOW() BETWEEN a.data_inicio AND a.data_fim
    """, (user_id,))
    active_subscriptions = cursor.fetchall()

    # 🔍 Busca todos os criadores disponíveis (apenas verificados)
    cursor.execute("""
        SELECT u.nome_usuario, p.profile_picture_url 
        FROM perfis_criadores p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE u.status_verificacao = 'verificado'  -- Filtra apenas criadores verificados
        ORDER BY u.nome_usuario ASC
    """)
    creators = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('creators_list.html', creators=creators, active_subscriptions=active_subscriptions)

@app.route('/check_login')
def check_login():
    is_logged_in = session.get("user_id") is not None  # Verifica se há um ID de usuário
    return jsonify({"is_logged_in": is_logged_in})

@app.route('/creator/<username>')
def creator_details(username):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 🔹 Buscar os dados do criador
        cursor.execute("""
            SELECT p.display_name, p.description, p.theme_color, p.profile_picture_url, p.cover_photo_url, p.valor_assinatura, u.id
            FROM perfis_criadores p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE u.nome_usuario = %s
        """, (username,))
        creator = cursor.fetchone()

        if not creator:
            flash("Criador não encontrado.", 'error')
            return redirect(url_for('creators_list'))

        display_name, description, theme_color, profile_picture, cover_photo, valor_assinatura, creator_id = creator

        # 🔹 Verifica se o usuário está logado
        user_id = session.get("user_id")
        is_logged_in = user_id is not None

        # 🔹 Verifica se o usuário logado é o próprio criador
        if is_logged_in and session['username'] == username:
            # Se for o próprio criador, redireciona para o dashboard
            return redirect(url_for('dashboard', username=username))

        # 🔹 Verifica se o usuário logado tem uma assinatura ativa e válida para o criador
        has_active_subscription = False
        if is_logged_in:
            cursor.execute("""
                SELECT status FROM assinaturas 
                WHERE usuario_id = %s 
                AND criador_assinado = %s 
                AND status = 'ativo'
                AND NOW() BETWEEN data_inicio AND data_fim
            """, (user_id, username))
            assinatura = cursor.fetchone()
            has_active_subscription = assinatura is not None

        # 🔹 Contar o número de mídias disponíveis
        cursor.execute("""
            SELECT COUNT(*) FROM media 
            WHERE usuario_id = %s AND status = 'disponivel' AND is_free = FALSE
        """, (creator_id,))
        total_midia = cursor.fetchone()[0]

        # 🔹 Preparar os dados para o template
        creator_data = {
            "username": username,
            "display_name": display_name,
            "description": description,
            "theme_color": theme_color,
            "profile_picture": profile_picture if profile_picture else 'default_profile_picture.jpg',
            "cover_photo": cover_photo if cover_photo else 'default_cover_photo.jpg',
            "valor_assinatura": valor_assinatura,
            "total_midia": total_midia,
            "is_logged_in": is_logged_in,  # Indica se o usuário está logado
            "has_active_subscription": has_active_subscription  # Indica se o usuário tem assinatura ativa
        }

        return render_template("creator_details.html", creator=creator_data)

    except Exception as e:
        flash(f"Erro ao carregar perfil do criador: {str(e)}", 'error')
        return redirect(url_for('creators_list'))

    finally:
        cursor.close()
        conn.close()

@app.route('/check_subscription/<username>')
def check_subscription(username):
    # Verifica se o usuário está logado
    if 'username' not in session or 'user_id' not in session:
        # Redireciona para a página pública do criador (sem mensagem de erro)
        return redirect(url_for('creator_details', username=username))

    user_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verifica se o usuário tem uma assinatura ativa para o criador
        cursor.execute("""
            SELECT status FROM assinaturas 
            WHERE usuario_id = %s 
            AND criador_assinado = %s 
            AND status = 'ativo'
            AND NOW() BETWEEN data_inicio AND data_fim  -- Adicionado esta linha
        """, (user_id, username))
        assinatura = cursor.fetchone()
        cursor.fetchall()  # Limpa resultados pendentes

        if assinatura:
            # Se tiver assinatura ativa, redireciona para o dashboard
            return redirect(url_for('dashboard', username=username))
        else:
            # Se não tiver assinatura ativa, redireciona para creator_details
            return redirect(url_for('creator_details', username=username))

    except Exception as e:
        flash(f"Erro ao verificar assinatura: {str(e)}", 'error')
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()

@app.route('/toggle_like/<username>', methods=['POST'])
def toggle_like(username):
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 403

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Buscar ID do criador
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
        criador = cursor.fetchone()
        if not criador:
            return jsonify({'error': 'Criador não encontrado'}), 404
        criador_id = criador[0]

        # Verificar se já existe uma curtida
        cursor.execute("SELECT id FROM curtidas WHERE usuario_id = %s AND criador_id = %s", (user_id, criador_id))
        curtida = cursor.fetchone()

        if curtida:
            # Se já curtiu, remover a curtida
            cursor.execute("DELETE FROM curtidas WHERE usuario_id = %s AND criador_id = %s", (user_id, criador_id))
            conn.commit()
            message = "Você removeu sua curtida."
            liked = False
        else:
            # Se ainda não curtiu, adicionar curtida
            cursor.execute("INSERT INTO curtidas (usuario_id, criador_id) VALUES (%s, %s)", (user_id, criador_id))
            conn.commit()
            message = "Você curtiu este criador!"
            liked = True

        # Retornar o número atualizado de curtidas
        cursor.execute("SELECT COUNT(*) FROM curtidas WHERE criador_id = %s", (criador_id,))
        total_curtidas = cursor.fetchone()[0]

        return jsonify({
            'liked': liked,  # Indica se o usuário curtiu ou removeu a curtida
            'total_likes': total_curtidas,  # Total de curtidas atualizado
            'message': message  # Mensagem de sucesso
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Buscar total de curtidas para um criador
@app.route('/get_likes/<username>', methods=['GET'])
def get_likes(username):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
        criador = cursor.fetchone()
        if not criador:
            return jsonify({'error': 'Criador não encontrado'}), 404
        criador_id = criador[0]

        cursor.execute("SELECT COUNT(*) FROM curtidas WHERE criador_id = %s", (criador_id,))
        total_curtidas = cursor.fetchone()[0]

        return jsonify({'total_likes': total_curtidas})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/seguir/<username>', methods=['POST'])
def seguir_criador(username):
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 🔹 Busca o ID do criador pelo username
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
        criador = cursor.fetchone()
        if not criador:
            return jsonify({"error": "Criador não encontrado"}), 404

        criador_id = criador[0]

        # 🔹 Verifica se o usuário já segue o criador
        cursor.execute("SELECT id FROM seguidores WHERE usuario_id = %s AND criador_id = %s", (user_id, criador_id))
        seguidor_existe = cursor.fetchone()

        if seguidor_existe:
            # 🔹 Se já segue, remove o seguidor
            cursor.execute("DELETE FROM seguidores WHERE usuario_id = %s AND criador_id = %s", (user_id, criador_id))
            conn.commit()
            following = False
            mensagem = "Você deixou de seguir este criador."
        else:
            # 🔹 Se não segue, adiciona o seguidor
            cursor.execute("INSERT INTO seguidores (usuario_id, criador_id) VALUES (%s, %s)", (user_id, criador_id))
            conn.commit()
            following = True
            mensagem = "Agora você segue este criador!"

        # 🔹 Retorna o total atualizado de seguidores
        cursor.execute("SELECT COUNT(*) FROM seguidores WHERE criador_id = %s", (criador_id,))
        total_seguidores = cursor.fetchone()[0]

        return jsonify({"success": True, "following": following, "total_followers": total_seguidores, "message": mensagem})

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/seguidores/<username>')
def listar_seguidores(username):
    if 'user_id' not in session:
        flash("Você precisa estar logado para acessar esta página.", 'error')
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verifica se o criador existe
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
        criador = cursor.fetchone()
        if not criador:
            flash("Criador não encontrado.", 'error')
            return redirect(url_for('index'))
        
        criador_id = criador['id']
        
        # Verifica se o usuário logado é o próprio criador
        if user_id != criador_id:
            flash("Você não tem permissão para acessar esta página.", 'error')
            return redirect(url_for('index'))
        
        # Busca a lista de seguidores
        cursor.execute("""
            SELECT u.id, u.nome_usuario
            FROM seguidores s
            JOIN usuarios u ON s.usuario_id = u.id
            WHERE s.criador_id = %s
        """, (criador_id,))
        seguidores = cursor.fetchall()
        
        return render_template('seguidores.html', seguidores=seguidores, username=username)
    except Exception as e:
        flash(f"Erro ao carregar a lista de seguidores: {str(e)}", 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

@app.route('/get_followers/<username>', methods=['GET'])
def get_followers(username):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Busca o ID do criador
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
        criador = cursor.fetchone()
        if not criador:
            return jsonify({'error': 'Criador não encontrado'}), 404

        criador_id = criador[0]

        # Conta o número de seguidores
        cursor.execute("SELECT COUNT(*) FROM seguidores WHERE criador_id = %s", (criador_id,))
        total_seguidores = cursor.fetchone()[0]

        return jsonify({'total_followers': total_seguidores})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/conversas', methods=['GET'])
def conversas():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    user_id = session['user_id']
    criador_id = request.args.get('criador_id')
    conversa_aberta_id = request.args.get('conversa_aberta_id')  # Novo parâmetro

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT tipo_usuario FROM usuarios WHERE id = %s", (user_id,))
        usuario = cursor.fetchone()
        conversas = []

        if usuario and usuario['tipo_usuario'] == 'criador':
            # Query modificada para ignorar contagem da conversa aberta
            cursor.execute("""
                SELECT u.id, u.nome_usuario, 
                       COALESCE(SUM(
                           CASE 
                               WHEN m.lida = FALSE AND (%s IS NULL OR u.id != %s) THEN 1 
                               ELSE 0 
                           END
                       ), 0) AS nao_lidas
                FROM seguidores s
                JOIN usuarios u ON s.usuario_id = u.id
                LEFT JOIN mensagens m ON m.remetente_id = u.id 
                                      AND m.destinatario_id = %s
                WHERE s.criador_id = %s
                GROUP BY u.id, u.nome_usuario
                
                UNION
                
                SELECT u.id, u.nome_usuario, 
                       COALESCE(SUM(
                           CASE 
                               WHEN m.lida = FALSE AND (%s IS NULL OR u.id != %s) THEN 1 
                               ELSE 0 
                           END
                       ), 0) AS nao_lidas
                FROM mensagens m
                JOIN usuarios u ON m.remetente_id = u.id
                WHERE m.destinatario_id = %s AND u.id != %s
                GROUP BY u.id, u.nome_usuario
            """, (conversa_aberta_id, conversa_aberta_id, user_id, user_id, 
                  conversa_aberta_id, conversa_aberta_id, user_id, user_id))

            conversas = cursor.fetchall()
            conversas.sort(key=lambda x: x['nome_usuario'])

        else:
            cursor.execute("""
                SELECT u.id, u.nome_usuario, 
                       CASE WHEN %s = %s THEN 0 ELSE 0 END AS nao_lidas
                FROM usuarios u
                WHERE u.id = %s
            """, (user_id, criador_id, criador_id))
            criador = cursor.fetchone()

            if criador:
                conversas.append(criador)

        return jsonify({"success": True, "conversas": conversas}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/mensagens_usuario/<int:usuario_id>', methods=['GET'])
def mensagens_usuario(usuario_id):
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    user_id = session['user_id']  # ID do usuário logado
    criador_id = request.args.get('criador_id')  # ID do criador acessado

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Busca todas as mensagens entre o usuário logado e o criador específico
        cursor.execute("""
            SELECT m.id, m.mensagem, m.data_envio, u.nome_usuario as remetente,
                   m.apagada_para_remetente, m.apagada_para_destinatario
            FROM mensagens m
            JOIN usuarios u ON m.remetente_id = u.id
            WHERE ((m.remetente_id = %s AND m.destinatario_id = %s)
               OR (m.remetente_id = %s AND m.destinatario_id = %s))
               AND (m.apagada_para_remetente = FALSE OR m.remetente_id != %s)
               AND (m.apagada_para_destinatario = FALSE OR m.destinatario_id != %s)
            ORDER BY m.data_envio ASC
        """, (user_id, usuario_id, usuario_id, user_id, user_id, user_id))
        mensagens = cursor.fetchall()

        # Sanitizar todas as mensagens antes de retornar
        for msg in mensagens:
            msg['mensagem'] = sanitize_input(msg['mensagem'])
            msg['remetente'] = sanitize_input(msg['remetente'])

        return jsonify({"success": True, "mensagens": mensagens}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/apagar_mensagem/<int:mensagem_id>', methods=['POST'])
def apagar_mensagem(mensagem_id):
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Marca a mensagem como apagada para o usuário atual
        cursor.execute("""
            UPDATE mensagens
            SET apagada_para_remetente = CASE
                WHEN remetente_id = %s THEN TRUE
                ELSE apagada_para_remetente
            END,
            apagada_para_destinatario = CASE
                WHEN destinatario_id = %s THEN TRUE
                ELSE apagada_para_destinatario
            END
            WHERE id = %s
        """, (user_id, user_id, mensagem_id))
        conn.commit()
        return jsonify({"success": True, "message": "Mensagem apagada com sucesso!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/apagar_todas_mensagens/<int:destinatario_id>', methods=['POST'])
def apagar_todas_mensagens(destinatario_id):
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Atualiza apenas as mensagens do usuário logado, sem afetar o outro usuário
        cursor.execute("""
            UPDATE mensagens
            SET apagada_para_remetente = CASE 
                WHEN remetente_id = %s THEN TRUE 
                ELSE apagada_para_remetente 
            END,
            apagada_para_destinatario = CASE 
                WHEN destinatario_id = %s THEN TRUE 
                ELSE apagada_para_destinatario 
            END
            WHERE (remetente_id = %s AND destinatario_id = %s)
               OR (remetente_id = %s AND destinatario_id = %s)
        """, (user_id, user_id, user_id, destinatario_id, destinatario_id, user_id))

        conn.commit()
        return jsonify({"success": True, "message": "Todas as suas mensagens desta conversa foram apagadas!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
                         
@app.route('/enviar_mensagem', methods=['POST'])
def enviar_mensagem():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    user_id = session['user_id']
    data = request.json
    destinatario_id = data.get('destinatario_id')
    mensagem = sanitize_input(data.get('mensagem'))  # Funciona se sua sanitize_input tratar None

    if not destinatario_id or not mensagem:
        return jsonify({"error": "Destinatário e mensagem são obrigatórios"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO mensagens (remetente_id, destinatario_id, mensagem, lida) 
            VALUES (%s, %s, %s, 0)
        """, (user_id, destinatario_id, mensagem))
        conn.commit()
        return jsonify({"success": True, "message": "Mensagem enviada com sucesso!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/ler_mensagens', methods=['GET'])
def ler_mensagens():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403

    user_id = session['user_id']
    destinatario_id = request.args.get('destinatario_id')  # ID do criador

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Busca todas as mensagens entre o usuário logado e o criador
        cursor.execute("""
            SELECT m.id, m.mensagem, m.data_envio, u.nome_usuario as remetente
            FROM mensagens m
            JOIN usuarios u ON m.remetente_id = u.id
            WHERE (m.remetente_id = %s AND m.destinatario_id = %s)
               OR (m.remetente_id = %s AND m.destinatario_id = %s)
            ORDER BY m.data_envio DESC
        """, (user_id, destinatario_id, destinatario_id, user_id))
        mensagens = cursor.fetchall()

        return jsonify({"success": True, "mensagens": mensagens}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/contar_mensagens_nao_lidas', methods=['GET'])
def contar_mensagens_nao_lidas():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403
    user_id = session['user_id']
    conversa_aberta_id = request.args.get('conversa_aberta_id')  # ID da conversa ativa
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT COUNT(*) 
            FROM mensagens 
            WHERE destinatario_id = %s 
              AND lida = FALSE
        """
        params = [user_id]
        if conversa_aberta_id:
            query += " AND remetente_id != %s"
            params.append(conversa_aberta_id)
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        return jsonify({"success": True, "count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
            
@app.route('/mensagens/<username>')
def mensagens(username):
    if 'username' not in session or 'user_id' not in session:
        flash("Você precisa estar logado para acessar as mensagens.", 'error')
        return redirect(url_for('index'))

    # Sanitização dos inputs
    username = sanitize_input(username)  # Sanitiza o username da URL

    # Busca o ID do criador com base no username
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (username,))
    criador = cursor.fetchone()
    if not criador:
        flash("Criador não encontrado.", 'error')
        return redirect(url_for('index'))
    criador_id = criador['id']
    user_id = session['user_id']

    # Busca o destinatario_id com base no username passado na URL
    destinatario_username = request.args.get('destinatario_username')
    if destinatario_username:
        destinatario_username = sanitize_input(destinatario_username)
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (destinatario_username,))
        destinatario = cursor.fetchone()
        if not destinatario:
            flash("Destinatário não encontrado.", 'error')
            return redirect(url_for('dashboard', username=username))
        destinatario_id = destinatario['id']
    else:
        destinatario_id = None

    # Busca as conversas
    cursor.execute("""
        SELECT u.id, u.nome_usuario, 
               COALESCE(SUM(CASE WHEN m.lida = 0 THEN 1 ELSE 0 END), 0) AS nao_lidas
        FROM seguidores s
        JOIN usuarios u ON s.usuario_id = u.id
        LEFT JOIN mensagens m ON m.remetente_id = u.id 
                              AND m.destinatario_id = %s 
                              AND m.lida = FALSE
        WHERE s.criador_id = %s
        GROUP BY u.id, u.nome_usuario
        UNION
        SELECT u.id, u.nome_usuario, 
               COALESCE(SUM(CASE WHEN m.lida = 0 THEN 1 ELSE 0 END), 0) AS nao_lidas
        FROM mensagens m
        JOIN usuarios u ON m.remetente_id = u.id
        WHERE m.destinatario_id = %s AND u.id != %s
        GROUP BY u.id, u.nome_usuario
    """, (user_id, criador_id, user_id, user_id))
    conversas = cursor.fetchall()
    
    # SANITIZAÇÃO ADICIONADA AQUI (sem alterar a lógica existente)
    for conversa in conversas:
        conversa['nome_usuario'] = sanitize_input(conversa['nome_usuario'])
    
    conversas.sort(key=lambda x: x['nome_usuario'])

    if destinatario_id:
        try:
            cursor.execute("""
                UPDATE mensagens
                SET lida = TRUE
                WHERE remetente_id = %s AND destinatario_id = %s AND lida = FALSE
            """, (destinatario_id, user_id))
            conn.commit()
        except Exception as e:
            print(f"Erro ao atualizar mensagens: {e}")
            conn.rollback()

    cursor.close()
    conn.close()

    return render_template('mensagens.html', 
                         criador_id=criador_id, 
                         user_id=user_id, 
                         username=username, 
                         destinatario_id=destinatario_id,
                         conversas=conversas)

@socketio.on('join')
def handle_join(data):
    user_id = data.get('user_id')
    if user_id:
        join_room(f'user_{user_id}')
        print(f'Usuário {user_id} entrou na sala user_{user_id}')

@socketio.on('message')
def handle_message(data):
    try:

        # Sanitizar a mensagem recebida
        data['mensagem'] = sanitize_input(data['mensagem'])

        remetente_id = data['remetente_id']
        destinatario_id = data['destinatario_id']
        mensagem = data['mensagem']
        conversa_aberta_com = data.get('conversa_aberta_com')  # <-- NOVO

        lida = False
        if conversa_aberta_com and str(conversa_aberta_com) == str(remetente_id):
            lida = True  # mensagem já lida pois usuário está com conversa aberta

        # Salva no banco de dados com o campo 'lida' atualizado
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mensagens (remetente_id, destinatario_id, mensagem, data_envio, lida)
            VALUES (%s, %s, %s, NOW(), %s)
        """, (remetente_id, destinatario_id, mensagem, lida))
        conn.commit()
        cursor.close()
        conn.close()

        # Busca nome do remetente
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nome_usuario FROM usuarios WHERE id = %s", (remetente_id,))
        remetente_nome = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        # Envia para ambos
        emit('new_message', {
            'remetente_id': remetente_id,
            'destinatario_id': destinatario_id,
            'mensagem': mensagem,
            'remetente': remetente_nome,
            'data_envio': datetime.now().isoformat()
        }, room=f'user_{destinatario_id}')

        emit('new_message', {
            'remetente_id': remetente_id,
            'destinatario_id': destinatario_id,
            'mensagem': mensagem,
            'remetente': remetente_nome,
            'data_envio': datetime.now().isoformat()
        }, room=f'user_{remetente_id}')

        # Só emitir contador se a mensagem realmente estiver não lida
        if not lida:
            emit('update_unread_count', {
                'destinatario_id': destinatario_id,
                'remetente_id': remetente_id
            }, broadcast=True)

    except Exception as e:
        print(f'Erro no handle_message: {e}')

@app.route('/usuario/<int:usuario_id>', methods=['GET'])
def usuario(usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, nome_usuario FROM usuarios WHERE id = %s", (usuario_id,))
        usuario = cursor.fetchone()
        if usuario:
            # Sanitizar o nome do usuário antes de retornar
            usuario['nome_usuario'] = sanitize_input(usuario['nome_usuario'])
            return jsonify(usuario), 200
        else:
            return jsonify({"error": "Usuário não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/marcar_mensagens_como_lidas/<int:remetente_id>', methods=['POST'])
def marcar_mensagens_como_lidas(remetente_id):
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 403
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE mensagens
            SET lida = TRUE
            WHERE remetente_id = %s AND destinatario_id = %s AND lida = FALSE
        """, (remetente_id, user_id))
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
        
# Dicionário para armazenar as salas de transmissão
live_connections = {}  # Nova estrutura para gerenciar conexões ativas

@app.route('/start_live/<username>', methods=['POST'])
def start_live(username):
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 403
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM perfis_criadores WHERE usuario_id = %s", (session['user_id'],))
        if not cursor.fetchone():
            return jsonify({'error': 'Usuário não é um criador'}), 403
        
        cursor.execute("UPDATE perfis_criadores SET is_live = TRUE WHERE usuario_id = %s", (session['user_id'],))
        conn.commit()
        
        # Apenas marca a live como ativa, sem tentar pegar o SID aqui
        if username not in live_connections:
            live_connections[username] = {
                'viewers': {},
                'is_live': True,
                'host_ready': False  # Será marcado como True quando o criador enviar 'creator_ready'
            }

        socketio.emit('live_status_update', {'username': username, 'is_live': True})
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"❌ Erro ao iniciar live: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get_token/<username>')
def get_token(username):
    try:
        is_owner = request.args.get('is_owner', 'false').lower() == 'true'
        creator = request.args.get('creator', username)  # Obtém o nome do criador
        
        # Usa o nome do criador para a sala
        room_name = f"room_{creator}"
        
        grants = {
            "roomJoin": True,
            "room": room_name,  # Usa o nome da sala do criador
            "canPublish": is_owner,
            "canSubscribe": True,  # PERMISSÃO CRUCIAL
            "canPublishData": is_owner,
            "roomAdmin": is_owner,
            "hidden": False,
            "roomList": True
        }
        
        token = jwt.encode({
            "iss": "LK_81aa40014b4e14de",
            "nbf": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=6),
            "sub": username,
            "video": grants,
            "metadata": json.dumps({"username": username})
        }, "e8fd328ab2a95f7b230e3dbb0185a5d9", algorithm="HS256")
        
        print(f"Token gerado para {username} (sala: {room_name}): {token}")  # LOG ADICIONAL
        return jsonify({
            "token": token,
            "ws_url": "ws://localhost:8080"
        })
    except Exception as e:
        print(f"ERRO TOKEN: {str(e)}")
        return jsonify({"error": str(e)}), 500

@socketio.on('creator_ready')
def handle_creator_ready(data):
    username = data['username']
    sid = request.sid
    if username not in live_connections:
        live_connections[username] = {
            'viewers': {},
            'is_live': True,
            'host_ready': True,
            'sid': sid
        }
    else:
        live_connections[username].update({
            'sid': sid,
            'host_ready': True,
            'is_live': True
        })
    print(f"👑 Criador {username} pronto (SID: {sid})")

@app.route('/stop_live/<username>', methods=['POST'])
def stop_live(username):
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não autenticado'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Notifica os espectadores antes de remover a live
        if username in live_connections:
            for viewer_sid in live_connections[username]['viewers'].values():
                socketio.emit('live_stopped', {'creator': username}, room=viewer_sid)
            del live_connections[username]
        
        # Atualiza o status do criador para offline no banco de dados
        cursor.execute("UPDATE perfis_criadores SET is_live = FALSE WHERE usuario_id = %s", (session['user_id'],))
        conn.commit()

        # Emite um evento global informando que a live foi encerrada
        socketio.emit('live_status_update', {'username': username, 'is_live': False}, namespace='/')

        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/live/<username>')
def live(username):
    # Verifica se o usuário está logado
    user_id: Optional[int] = session.get("user_id")
    if user_id is None:
        flash("Você precisa estar logado para acessar a live.", 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Busca os dados do perfil do criador
        cursor.execute("""
            SELECT p.display_name, p.description, p.theme_color, p.profile_picture_url, p.cover_photo_url, p.is_live
            FROM perfis_criadores p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE u.nome_usuario = %s
        """, (username,))
        profile = cursor.fetchone()

        if not profile:
            flash("Perfil não encontrado.", 'error')
            return redirect(url_for('index'))

        profile_data = {
            'display_name': profile[0],
            'description': profile[1],
            'theme_color': profile[2],
            'profile_picture_url': profile[3],
            'cover_photo_url': profile[4],
            'is_live': profile[5],  # Passa o estado da live para o template
            'username': username
        }

        # Verifica se o usuário logado é o criador da live
        is_owner = session.get('username') == username

        # Se a live não estiver ativa e o usuário não for o criador, redireciona para o dashboard
        if not profile_data['is_live'] and not is_owner:
            return redirect(url_for('dashboard'))

        return render_template(
            'live.html',
            profile=profile_data,  # Passa os dados do perfil para o template
            username=username,
            is_owner=is_owner
        )

    except Exception as e:
        print(f"❌ Erro ao carregar a live: {e}")
        flash("Ocorreu um erro ao carregar a live. Tente novamente mais tarde.", 'error')
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()  

@app.route('/check_live_status/<username>', methods=['GET'])
def check_live_status(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Verifica se o usuário atual é o dono
        is_owner = 'user_id' in session and session.get('username') == username
        
        # Verifica status da live
        cursor.execute("""
            SELECT is_live FROM perfis_criadores 
            WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
        """, (username,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'Perfil não encontrado'}), 404
            
        return jsonify({
            'is_live': bool(result[0]),
            'is_owner': is_owner,
            'message': 'Live ativa' if result[0] else 'Live offline'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@socketio.on('connect')
def handle_connect():
    try:
        print(f'Client connected: {request.sid}')
        emit('connection_ack', {'status': 'success'})
    except Exception as e:
        print(f'Erro na conexão: {str(e)}')
        emit('connection_error', {'error': str(e)})

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"Cliente desconectado: {sid}")
    
    # Verifica se é um criador desconectando
    for creator, data in list(live_connections.items()):
        if data.get('sid') == sid:
            print(f"Criador {creator} desconectado, encerrando live")
            # Notifica todos os espectadores
            for viewer_sid in data.get('viewers', {}).values():
                emit('live_ended', {'creator': creator}, room=viewer_sid)
            
            # Atualiza o status no banco de dados
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE perfis_criadores SET is_live = FALSE 
                WHERE usuario_id = (SELECT id FROM usuarios WHERE nome_usuario = %s)
            """, (creator,))
            conn.commit()
            conn.close()
            
            # Remove a live
            if creator in live_connections:
                del live_connections[creator]
            break            

@socketio.on('join_live')
def handle_join_live(data):
    username = data['username']
    sid = request.sid  # Captura o SID corretamente no WebSocket
    print(f"👤 {username} entrou na live (SID: {sid})")

    join_room(username)  # Criador e espectadores entram na sala da live

    if username in live_connections:
        live_connections[username]["sid"] = sid  # Atualiza o SID do criador
    else:
        live_connections[username] = {
            "sid": sid,
            "viewers": {},
            "is_live": True,
            "host_ready": True
        }

@socketio.on("request_offer")
def handle_request_offer(data):
    creator = data["creator"]
    viewer = data["viewer"]
    viewer_sid = request.sid  # SID do espectador

    if creator not in live_connections or not live_connections[creator].get('host_ready'):
        print(f"❌ Criador {creator} não está pronto para receber espectadores")
        emit("live_not_available", {"creator": creator}, room=viewer_sid)
        return

    # Registra o espectador
    live_connections[creator]["viewers"][viewer] = viewer_sid
    
    # Envia para o criador
    emit("new_viewer", {
        "viewer": viewer,
        "sid": viewer_sid
    }, room=live_connections[creator]["sid"])

@socketio.on('leave_live')
def handle_leave_live(data):
    username = data['username']
    creator = data['creator']
    
    if creator in live_connections and username in live_connections[creator]['viewers']:
        del live_connections[creator]['viewers'][username]        

@app.route('/connection_status/<username>', methods=['GET'])
def connection_status(username):
    if username not in live_connections:
        return jsonify({'error': 'Live não encontrada'}), 404
    return jsonify({
        'viewers_count': len(live_connections[username]['viewers']),
        'is_live': live_connections[username]['is_live'],
        'host_ready': live_connections[username]['host_ready']
    })

@socketio.on('start_watching')
def handle_start_watching(data):
    try:
        username = data['username']
        creator = data['creator']
        sid = request.sid
        
        print(f"👀 {username} começou a assistir a live de {creator}.")
        
        if creator in live_connections:
            # Adiciona o espectador à lista de viewers
            live_connections[creator]['viewers'][username] = sid
            print(f"Espectador {username} registrado (SID: {sid})")
            
            if 'sid' in live_connections[creator]:
                emit("request_offer", {
                    "viewer": username,  # Corrigido de "viewer" para "viewer"
                    "creator": creator,
                    "sid": sid
                }, room=live_connections[creator]['sid'])
            else:
                emit("live_not_available", {"creator": creator}, room=sid)
        else:
            emit("live_not_available", {"creator": creator}, room=sid)
            print(f"Live do criador {creator} não encontrada")
            
    except Exception as e:
        print(f"Erro em start_watching: {str(e)}")
        emit("error", {"message": str(e)}, room=request.sid)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/check_livekit_server')
def check_livekit_server():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('localhost', 8080))
        s.close()
        return jsonify({'status': 'online'})
    except Exception as e:
        return jsonify({'status': 'offline', 'error': str(e)}), 503
    
@app.route('/test_token')
def test_token():
    try:
        token = generate_livekit_token(
            api_key="LK_81aa40014b4e14de",
            api_secret="e8fd328ab2a95f7b230e3dbb0185a5d9",
            identity="test_user",
            room="test_room",
            is_owner=True
        )
        
        return jsonify({
            'token': token,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500   

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/livekit/health')
def livekit_health():
    try:
        # Verifica se o servidor LiveKit está acessível
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('localhost', 8080))  # Altere a porta conforme necessário
        s.close()
        
        return jsonify({
            'status': 'online',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': {
                'flask': 'online',
                'livekit': 'online'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'offline',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'details': {
                'flask': 'online',
                'livekit': 'offline',
                'error': str(e)
            }
        }), 503
    
@app.route('/validate_token/<token>')
def validate_token(token):
    try:
        print(f"🔍 Token recebido: {token}")  # Debug para ver se o token chega corretamente

        decoded = jwt.decode(token, "e8fd328ab2a95f7b230e3dbb0185a5d9", algorithms=["HS256"])
        
        return jsonify({
            'valid': True,
            'data': decoded,
            'expires': datetime.fromtimestamp(decoded['exp']).isoformat()
        })
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'Token expirado'}), 400
    except jwt.InvalidTokenError as e:
        return jsonify({'valid': False, 'error': str(e)}), 400


@app.route('/server_time')
def server_time():
    # Usa timestamp UNIX que é universal
    return jsonify({
        'server_timestamp': time.time(),
        'timezone': 'UTC'
    })

@app.route('/livekit/debug')
def livekit_debug():
    try:
        # Teste de conexão básica
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('localhost', 8080))
        s.close()
        
        # Teste de token
        test_token = generate_livekit_token(
            api_key="LK_81aa40014b4e14de",
            api_secret="e8fd328ab2a95f7b230e3dbb0185a5d9",
            identity="test_user",
            room="test_room",
            is_owner=True
        )
        
        return jsonify({
            'status': 'online',
            'port': 8080,
            'token_test': {
                'generated': True,
                'length': len(test_token)
            },
            'config': {
                'api_key': 'LK_81aa40014b4e14de',
                'api_secret': 'e8fd328ab2a95f7b230e3dbb0185a5d9'[:4] + '...'  # Não mostra o segredo completo
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Adicione junto com os outros handlers do Socket.IO

@socketio.on('chat_message')
def handle_chat_message(data):
    # Aplica sanitize_input a todos os campos relevantes
    sender = sanitize_input(data.get('sender', ''))
    recipient = sanitize_input(data.get('recipient', ''))  # Será None se for mensagem global
    message = sanitize_input(data.get('message', ''))

    if not sender or not message:
        return  # Ignora mensagens inválidas

    # Se for uma mensagem PRIVADA (espectador → criador)
    if recipient:
        # Verifica se o criador está online
        if recipient in live_connections:
            # Envia apenas para o criador da live
            emit('chat_message', {
                'sender': sender,
                'recipient': recipient,
                'message': message,
                'is_private': True  # Opcional: identificar como mensagem privada
            }, room=live_connections[recipient]['sid'])
    
    # Se for uma mensagem GLOBAL (criador → todos)
    else:
        # Verifica se o sender é um criador de live
        if sender in live_connections:
            # Envia para TODOS os espectadores da live
            emit('chat_message', {
                'sender': sender,
                'message': message,
                'is_private': False  # Opcional: identificar como mensagem pública
            }, broadcast=True)  # Envia para todos na sala (opcional, depende da estrutura)

            # OU, se estiver usando a estrutura de viewers:
            if 'viewers' in live_connections[sender]:
                for viewer_sid in live_connections[sender]['viewers'].values():
                    emit('chat_message', {
                        'sender': sender,
                        'message': message
                    }, room=viewer_sid)

@socketio.on('viewer_joined')
def handle_viewer_joined(data):
    creator_username = data.get('creator_username')
    if creator_username in live_connections:
        # Adiciona o espectador à lista
        live_connections[creator_username]['viewers'][request.sid] = True
        
        # Novo: Atualiza TODOS conectados à live
        emit_viewers_count(creator_username)

def emit_viewers_count(creator_username):
    if creator_username in live_connections:
        count = len(live_connections[creator_username]['viewers'])
        # Envia para o criador
        emit('viewers_update', count, room=live_connections[creator_username]['sid'])
        # Envia para todos espectadores
        for viewer_sid in live_connections[creator_username]['viewers']:
            emit('viewers_update', count, room=viewer_sid)

@socketio.on('get_viewers_count')
def handle_get_viewers_count(data):
    creator_username = data.get('creator_username')
    emit_viewers_count(creator_username)

@socketio.on('disconnect')
def handle_disconnect():
    # Remove o desconectado de todas as lives
    for creator in list(live_connections.keys()):
        if request.sid in live_connections[creator]['viewers']:
            live_connections[creator]['viewers'].pop(request.sid)
            emit_viewers_count(creator)
        elif request.sid == live_connections[creator]['sid']:
            # Se for o criador desconectando
            live_connections.pop(creator, None)  

if __name__ == '__main__':
    socketio.run(app, debug=True)

