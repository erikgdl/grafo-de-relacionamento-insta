import requests
import json
import time
import pandas as pd
import math
import concurrent.futures 
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
from dotenv import load_dotenv

# --- Configurações ---
load_dotenv()
QUERY_HASH_FOLLOWERS = os.getenv("QUERY2_HASH_FOLLOWERS")
QUERY_HASH_FOLLOWING = os.getenv("QUERY_HASH_FOLLOWING")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-IG-App-ID": "936619743392459"
}

# --- Sessão do Requests (Autenticação) ---
s = requests.Session()

SESSIONID_VALUE = os.getenv("SESSIONID_VALUE")
CSRFTOKEN_VALUE = os.getenv("CSRFTOKEN_VALUE")

s.cookies.set("sessionid", SESSIONID_VALUE)
s.cookies.set("csrftoken", CSRFTOKEN_VALUE)


# --- Coleta de Dados ---

def get_user_data(username):
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        res = s.get(url, headers=HEADERS)
        if res.status_code == 200:
            data = res.json()
            return data["data"]["user"]
        else:
            print(f"  -> Erro {res.status_code} ao buscar {username}. Pulando.")
            return None
    except Exception as e:
        print(f"  -> Exceção ao buscar {username}: {e}. Pulando.")
        return None

def get_user_id_from_username(username):
    data = get_user_data(username)
    if data:
        return data.get("id")
    return None

def fetch_graphql_list(user_id, query_hash, list_type_key, list_name, first=50, max_pages=None, sleep_between=1.5):
    """
    Função genérica para buscar Seguidores ou Seguindo.
    list_type_key: "edge_followed_by" (Seguidores) ou "edge_follow" (Seguindo)
    list_name: String para o print (ex: "Seguidores")
    """
    results = []
    after = None
    pages = 0
    
    if max_pages:
        print(f"Iniciando busca de {list_name} (GraphQL) com limite de {max_pages} páginas...")
    else:
        print(f"Iniciando busca de TODOS os {list_name} (GraphQL)...")
    
    while True:
        variables = {"id": str(user_id), "include_reel": True, "fetch_mutual": False, "first": first}
        if after:
            variables["after"] = after

        vars_encoded = json.dumps(variables, separators=(",", ":"))
        url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables={vars_encoded}"
        
        try:
            res = s.get(url, headers=HEADERS)
            
            if res.status_code != 200:
                print(f"Erro na GraphQL ({list_name}): {res.status_code}. Pausando 60s...")
                time.sleep(60)
                continue

            data = res.json()
            
            if "data" not in data or "user" not in data["data"] or list_type_key not in data["data"]["user"]:
                print(f"Erro: Resposta inesperada da GraphQL ({list_name}): {data}")
                print("Verifique seu 'sessionid'. Parando.")
                break
                
            edges = data["data"]["user"][list_type_key]["edges"]
            page_info = data["data"]["user"][list_type_key]["page_info"]

            for e in edges:
                node = e.get("node")
                results.append({
                    "username": node.get("username"),
                    "full_name": node.get("full_name"),
                    "pk": node.get("id"),
                    "is_private": node.get("is_private", False)
                })

            pages += 1
            print(f"Página {pages} carregada, {len(results)} {list_name} encontrados...")
            
            if max_pages and pages >= max_pages:
                print(f"Limite de {max_pages} páginas atingido.")
                break

            if page_info.get("has_next_page"):
                after = page_info.get("end_cursor")
                time.sleep(sleep_between)
            else:
                print(f"Fim da lista de {list_name}.")
                break
                
        except Exception as e:
            print(f"Exceção na GraphQL ({list_name}): {e}")
            break
            
    return results

def get_followers(username, limit_pages=None):
    print(f"\nBuscando ID do usuário para '{username}'...")
    uid = get_user_id_from_username(username)
    if not uid:
        print("ERRO FATAL: Não foi possível obter o ID do usuário.")
        return []
    print(f"ID encontrado: {uid}.")
    return fetch_graphql_list(uid, QUERY_HASH_FOLLOWERS, "edge_followed_by", "Seguidores", max_pages=limit_pages)

def get_following(username, limit_pages=None):
    print(f"\nBuscando ID do usuário para '{username}'...")
    uid = get_user_id_from_username(username)
    if not uid:
        print("ERRO FATAL: Não foi possível obter o ID do usuário.")
        return []
    print(f"ID encontrado: {uid}.")
    return fetch_graphql_list(uid, QUERY_HASH_FOLLOWING, "edge_follow", "Seguindo", max_pages=limit_pages)

def save_to_excel(data, filename):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"\n✅ Dados salvos com sucesso em {filename} ({len(data)} perfis)")

def organizar_em_pilhas(lista_pessoas, x_inicio_grupo, y_passo, pilhas_por_grupo):
    qtd_pessoas = len(lista_pessoas)
    posicoes_grupo = {}
    if qtd_pessoas == 0:
        return posicoes_grupo

    x_coluna_dist = 6
    pessoas_por_pilha = math.ceil(qtd_pessoas / pilhas_por_grupo) 
    if pessoas_por_pilha == 0:
        return posicoes_grupo
        
    for i, pessoa in enumerate(lista_pessoas):
        idx_pilha = i // pessoas_por_pilha 
        idx_na_pilha = i % pessoas_por_pilha 

        x = x_inicio_grupo + (idx_pilha * x_coluna_dist) 
        
        y_total_pilha = min(pessoas_por_pilha, qtd_pessoas - (idx_pilha * pessoas_por_pilha))
        y_start_pilha = (y_total_pilha - 1) * y_passo / 2
        
        y = y_start_pilha - idx_na_pilha * y_passo
        posicoes_grupo[pessoa] = (x, y)
        
    return posicoes_grupo

def draw_detailed_graph(target, followers_list, following_list):
    """
    Cria e salva um grafo detalhado com 3 colunas:
    - Só Seguidores
    - Mutuais
    - Só Seguindo
    """
    print("\nIniciando geração do grafo detalhado...")

    followers_set = {f.get("username") for f in followers_list if f.get("username")}
    following_set = {f.get("username") for f in following_list if f.get("username")}

    mutuais = list(following_set.intersection(followers_set))
    so_seguindo = list(following_set - followers_set)
    so_seguidores = list(followers_set - following_set)

    print(f"  - Total Seguidores: {len(followers_set)}")
    print(f"  - Total Seguindo: {len(following_set)}")
    print(f"  - Mutuais: {len(mutuais)}")
    print(f"  - Só Seguindo (você segue): {len(so_seguindo)}")
    print(f"  - Só Seguidores (te seguem): {len(so_seguidores)}")

    G = nx.DiGraph()
    G.add_node(target) 

    for pessoa in mutuais:
        G.add_node(pessoa)
        G.add_edge(target, pessoa) 
        G.add_edge(pessoa, target)
    
    for pessoa in so_seguindo:
        G.add_node(pessoa)
        G.add_edge(target, pessoa)
        
    for pessoa in so_seguidores:
        G.add_node(pessoa)
        G.add_edge(pessoa, target)

    pos = {target: (0, 0)}
    y_passo = 1.5
    pilhas_por_grupo = 3

    pos.update(organizar_em_pilhas(so_seguidores, -30, y_passo, pilhas_por_grupo)) 
    pos.update(organizar_em_pilhas(mutuais, -15, y_passo, pilhas_por_grupo)) 
    pos.update(organizar_em_pilhas(so_seguindo, 15, y_passo, pilhas_por_grupo)) 

    cores = []
    for node in G.nodes():
        if node == target:
            cores.append("gold")
        elif node in mutuais:
            cores.append("limegreen")
        elif node in so_seguindo:
            cores.append("skyblue")
        else:
            cores.append("lightcoral")

    try:
        mpl.rcParams['font.family'] = 'Comic Sans MS'
        mpl.rcParams['font.sans-serif'] = ['Comic Sans MS']
    except:
        print("A fonte 'Comic Sans MS' não foi encontrada. Usando fonte padrão.")
        mpl.rcParams['font.family'] = 'sans-serif'

    print("Desenhando o grafo (isso pode levar um minuto)...")
    plt.figure(figsize=(25, 18)) 

    nx.draw(
        G,
        pos, 
        with_labels=True,
        node_color=cores,
        node_size=1000, 
        font_size=8,   
        arrows=True,
        arrowsize=10,  
        font_weight="bold",
        edge_color='gray',
        alpha=0.8 
    )

    max_y = max([p[1] for p in pos.values()] + [10])
    y_legend_offset = max_y + 5
    x_coluna_dist = 6 

    plt.text(pos[target][0], pos[target][1] + 3, target, 
             fontsize=16, ha='center', color='black', bbox=dict(facecolor='gold', alpha=0.6, edgecolor='none'))

    if so_seguidores:
        plt.text(-30 + (x_coluna_dist * (pilhas_por_grupo-1))/2, y_legend_offset, 'Só te Seguem', 
                 fontsize=14, ha='center', color='black', bbox=dict(facecolor='lightcoral', alpha=0.6, edgecolor='none'))
    
    if mutuais:
        plt.text(-15 + (x_coluna_dist * (pilhas_por_grupo-1))/2, y_legend_offset, 'Mutuais', 
                 fontsize=14, ha='center', color='black', bbox=dict(facecolor='limegreen', alpha=0.6, edgecolor='none'))
    
    if so_seguindo:
        plt.text(15 + (x_coluna_dist * (pilhas_por_grupo-1))/2, y_legend_offset, 'Você Segue', 
                 fontsize=14, ha='center', color='black', bbox=dict(facecolor='skyblue', alpha=0.6, edgecolor='none'))

    plt.title(f"Grafo Detalhado de Relacionamentos de @{target}", fontsize=18)
    plt.axis('off') 
    
    # 8. Salva a imagem
    graph_filename = f"{target}_detailed_graph.png"
    plt.savefig(graph_filename)
    print(f"✅ Grafo salvo como {graph_filename}")
    # plt.show() # Descomente se quiser que ele abra a imagem


def process_follower(follower_data):
    idx, follower, total = follower_data
    try:
        username = follower.get("username")
        if not username:
            return None
        print(f"[{idx}/{total}] Buscando dados de: {username}")
        user_data = get_user_data(username)
        if user_data:
            street = None
            city = None
            address_json = user_data.get("business_address_json")
            if isinstance(address_json, dict):
                street = address_json.get("street_address")
                city = address_json.get("city_name")
            elif isinstance(address_json, str):
                try:
                    address_data = json.loads(address_json)
                    street = address_data.get("street_address")
                    city = address_data.get("city_name")
                except:
                    pass
            result_dict = {
                "Person username": user_data.get("username"),
                "Instagram Url": f"https://www.instagram.com/{username}/",
                "Full Name": user_data.get("full_name"),
                "Follower Count": user_data.get("edge_followed_by", {}).get("count"),
                "Following count": user_data.get("edge_follow", {}).get("count"),
                "Media count": user_data.get("edge_owner_to_timeline_media", {}).get("count"),
                "Biography": user_data.get("biography"),
                "External Url": user_data.get("external_url"),
                "Email": user_data.get("business_email"),
                "Contact Phone Number": user_data.get("business_phone_number"),
                "Address Street": street,
                "City Name": city,
                "Category": user_data.get("category_name")
            }
            time.sleep(0.3) 
            return result_dict
        return None
    except Exception as e:
        if 'username' in locals():
            print(f"  -> Erro inesperado ao processar {username}: {e}. Pulando...")
        else:
            print(f"  -> Erro inesperado ao processar seguidor #{idx}: {e}. Pulando...")
        return None


# --- Execução Principal ---

def main():
    target_profile = input("Qual o @ do perfil que você quer analisar? (ex: hyd_events) ")
    output_file = f"{target_profile}_instagram_data.xlsx"
    MAX_WORKERS = 5

    print(f"Alvo: {target_profile} | Buscando TODOS os seguidores e seguindo.")
    
    followers_list = get_followers(target_profile)
    if not followers_list:
        print("Não foi possível obter a lista de seguidores. Encerrando.")
        return
    
    following_list = get_following(target_profile)
    if not following_list:
        print("Não foi possível obter a lista de 'seguindo'. Encerrando.")
        return

    followers_to_process = followers_list
    total = len(followers_to_process)
    print(f"\nLista de {total} seguidores obtida. Iniciando raspagem de dados para o Excel...")

    tasks = []
    for idx, follower in enumerate(followers_to_process, 1):
        tasks.append((idx, follower, total))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        raw_results = executor.map(process_follower, tasks)
        for r in raw_results:
            if r is not None:
                results.append(r)

    if results:
        save_to_excel(results, output_file)
        draw_detailed_graph(target_profile, followers_list, following_list)
        
    else:
        print("Nenhum dado foi coletado. O arquivo Excel não foi criado.")


# --- Rodar o script ---
if __name__ == "__main__":
    main()