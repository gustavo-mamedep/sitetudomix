#Funções utéis para o sistema

from django.db.models import Max, Min
from django.core.mail import send_mail
from django.http import HttpResponse
import csv


def filtrar_produtos(produtos, filtro):
    if filtro:
        if "-" in filtro:
            categoria, subcategoria = filtro.split("-")
            produtos = produtos.filter(subcategoria__slug=subcategoria, categoria__slug=categoria)
        else:
            produtos = produtos.filter(categoria__slug=filtro)
    return produtos


def preco_minimo_maximo(produtos):
    minimo = 0
    maximo = 0
    if len(produtos) > 0:
        maximo = list(produtos.aggregate(Max("preco")).values())[0]
        maximo = round(maximo, 2)
        minimo = list(produtos.aggregate(Min("preco")).values())[0]
        minimo = round(minimo, 2)

    return minimo, maximo


def ordenar_produtos(produtos, ordem):
    if ordem == "menor-preco":
        produtos = produtos.order_by("preco")
    elif ordem == "maior-preco":
        produtos = produtos.order_by("-preco")   
    elif ordem == "mais-vendido":
        lista_produtos = []
        for produto in produtos:
            lista_produtos.append((produto.total_vendas(), produto))
            print(produto.nome, produto.total_vendas())
        lista_produtos = sorted(lista_produtos, key=lambda x: x[0], reverse=True)
        produtos = [item[1] for item in lista_produtos]
    return produtos


def enviar_email_compra(pedido):
    email = pedido.cliente.email
    assunto = f"Pedido {pedido.id} foi Aprovado!"
    corpo = f"""Seu pedido foi aprovado.
    Número do pedido: {pedido.id}
    Valor Total: {pedido.preco_total}
    Qualquer dúvida pode nos chamar no Whatsapp (34) 99877-4990"""
    remetente = "tudomixudi@gmail.com"
    send_mail(assunto, corpo, remetente, [email])


def exportar_csv(informacoes):
    colunas = informacoes.model._meta.fields
    nomes_colunas = [coluna.name for coluna in colunas]
    
    resposta = HttpResponse(content_type="text/csv")
    resposta["Content-Disposition"] = "attachment; filename=exportacao_tudomix.csv"

    criador_csv = csv.writer(resposta, delimiter=";")

    criador_csv.writerow(nomes_colunas)
    #escrever as linhas do arquivo
    for linha in informacoes.values_list():
        criador_csv.writerow(linha)

    
    return resposta

