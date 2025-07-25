from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import *
import uuid
from pybrcode.pix import generate_simple_pix
from .utils import filtrar_produtos, preco_minimo_maximo, ordenar_produtos, enviar_email_compra, exportar_csv
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from datetime import datetime
from .api_mercadopago import criar_pagamento

from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth import get_user_model




def setup_site(request):
    # ⚠️ Segurança: só deixe acessível enquanto estiver configurando
    if request.GET.get('token') != 'secreto123':
        return HttpResponse("Acesso negado.", status=403)

    # 1. Migrar o banco
    call_command('migrate')

    # 2. Criar superusuário padrão se não existir
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'gustavo@vestelivre.com.br', 'MAMEDE3276')

    # 3. Coletar os arquivos estáticos
    call_command('collectstatic', interactive=False)

    return HttpResponse("✅ Site configurado com sucesso!")






# Create your views here.
def homepage(request):
    banners = Banner.objects.filter(ativo=True)
    context = {"banners": banners}
    return render(request, 'homepage.html', context)




def loja(request, filtro=None):
    # 1) produtos iniciais (URL‐based filter)
    produtos = Produto.objects.filter(ativo=True)
    produtos = filtrar_produtos(produtos, filtro)

    # vamos capturar aqui se veio categoria via POST
    categoria_post = None

    # 2) aplicação de filtros via formulário
    if request.method == "POST":
        dados = request.POST.dict()

        # faixas de preço
        produtos = produtos.filter(
            preco__gte=dados.get("preco_minimo"),
            preco__lte=dados.get("preco_maximo")
        )

        # subcategoria via form
        if dados.get("subcategoria"):
            produtos = produtos.filter(subcategoria__slug=dados["subcategoria"])

        # categoria via form
        if dados.get("categoria"):
            produtos = produtos.filter(categoria__slug=dados["categoria"])
            categoria_post = dados["categoria"]

    # 3) preparo de subcategorias_navegacao
    if categoria_post:
        # usaremos a categoria do POST para listar suas subcategorias
        subcategorias_navegacao = Subcategoria.objects.filter(
            categoria__slug=categoria_post
        )
    elif filtro and "-" in filtro:
        # ex: /loja/relogios-45mm/
        slug_cat = filtro.split("-")[0]
        subcategorias_navegacao = Subcategoria.objects.filter(
            categoria__slug=slug_cat
        )
    elif filtro:
        # ex: /loja/relogios/
        subcategorias_navegacao = Subcategoria.objects.filter(
            categoria__slug=filtro
        )
    else:
        # sem filtro algum
        subcategorias_navegacao = Subcategoria.objects.all()

    # 4) categorias para cabeçalho e faixa de preço
    ids_cats = produtos.values_list("categoria", flat=True).distinct()
    categorias = Categoria.objects.filter(id__in=ids_cats)
    minimo, maximo = preco_minimo_maximo(produtos)

    # 5) ordenar e renderizar
    ordem = request.GET.get("ordem", "menor-preco")
    produtos = ordenar_produtos(produtos, ordem)

    return render(request, "loja.html", {
        "produtos": produtos,
        "minimo": minimo,
        "maximo": maximo,
        "categorias": categorias,
        "subcategorias_navegacao": subcategorias_navegacao,
        # opcional: repassar a categoria selecionada para manter selecionado no template
        "categoria_selecionada": categoria_post or filtro,
    })




def ver_produto(request, id_produto, id_cor=None):
    cor_selecionada = None
    if id_cor:
        cor = Cor.objects.get(id=id_cor)
        cor_selecionada = cor.nome
    produto = Produto.objects.get(id=id_produto)
    itens_estoque = ItemEstoque.objects.filter(produto=produto, quantidade__gt=0)
    if len(itens_estoque) > 0:
        tem_estoque = True
        cores = {item.cor for item in itens_estoque}
        if id_cor:
            itens_estoque = ItemEstoque.objects.filter(produto=produto, quantidade__gt=0, cor__id=id_cor)
    else:
        tem_estoque = False
        cores = {}
    similares = Produto.objects.filter(categoria__id=produto.categoria.id).exclude(id=produto.id)[:4]
    context = {"produto": produto,
               "itens_estoque": itens_estoque,
               "tem_estoque": tem_estoque,
               "cores": cores,
               "cor_selecionada": cor_selecionada,
               "id_cor": id_cor,
               "similares": similares,
    }
    return render(request, 'ver_produto.html', context)




def adicionar_carrinho(request, id_produto):
    if request.method == 'POST' and id_produto:
        dados = request.POST.dict()
        id_cor = dados.get('cor')
        # pegar cliente
        resposta = redirect('carrinho')
        if request.user.is_authenticated:
            cliente = request.user.cliente
        else:
            if request.COOKIES.get("id_sessao"):
                id_sessao = request.COOKIES.get("id_sessao")
            else:
                id_sessao = str(uuid.uuid4())
                resposta.set_cookie(key="id_sessao", value=id_sessao, max_age=60*60*24*30)
            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
        pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
        item_estoque = ItemEstoque.objects.get(produto__id =id_produto, cor__id=id_cor)
        item_pedido, criado = ItensPedido.objects.get_or_create(item_estoque=item_estoque, pedido=pedido)
        item_pedido.quantidade += 1
        item_pedido.save()
        return resposta
    else:
        return redirect('loja')




def remover_carrinho(request, id_produto):
    if request.method == 'POST' and id_produto:
        dados = request.POST.dict()
        id_cor = dados.get('cor')
        if request.user.is_authenticated:
            cliente = request.user.cliente
        else:
            if request.COOKIES.get("id_sessao"):
                id_sessao = request.COOKIES.get("id_sessao")
                cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
            else:
                return redirect('loja')
        pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
        item_estoque = ItemEstoque.objects.get(produto__id =id_produto, cor__id=id_cor)
        item_pedido, criado = ItensPedido.objects.get_or_create(item_estoque=item_estoque, pedido=pedido)
        item_pedido.quantidade -= 1
        item_pedido.save()
        if item_pedido.quantidade <= 0:
            item_pedido.delete()
        return redirect('carrinho')
    else:
        return redirect('loja')



def carrinho(request):
    if request.user.is_authenticated:
        cliente = request.user.cliente
    else:
        if request.COOKIES.get("id_sessao"):
            id_sessao = request.COOKIES.get("id_sessao")
            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
        else:
            context = {"cliente_existente": False, "itens_pedido": None, "pedido": None}
            return render(request, 'carrinho.html', context)
    pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
    itens_pedido = ItensPedido.objects.filter(pedido=pedido)
    context = {"itens_pedido": itens_pedido, "pedido": pedido, "cliente_existente": True}
    return render(request, 'carrinho.html', context)




def checkout(request):
    if request.user.is_authenticated:
        cliente = request.user.cliente
    else:
        if request.COOKIES.get("id_sessao"):
            id_sessao = request.COOKIES.get("id_sessao")
            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
        else:
            return redirect('loja')
    pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
    enderecos = Endereco.objects.filter(cliente=cliente)
    context = {"pedido": pedido, "enderecos": enderecos, "erro": None}
    return render(request, 'checkout.html', context)



def finalizar_pedido(request, id_pedido):
    if request.method == "POST":
        erro = None
        dados = request.POST.dict()
    
        total = dados.get("total")
        total = float(total.replace(",", "."))
        pedido = Pedido.objects.get(id=id_pedido)
        if total != float(pedido.preco_total):
            erro = "preco"
        if not "endereco" in dados:
            erro = "endereco"
        else:
            id_endereco = dados.get("endereco")
            endereco = Endereco.objects.get(id=id_endereco)
            pedido.endereco = endereco
        if not request.user.is_authenticated:
            email = dados.get("email")
            try:
                validate_email(email)
            except ValidationError:
                erro = "email"
            if not erro:
                clientes = Cliente.objects.filter(email=email)
                if clientes:
                    pedido.cliente = clientes[0]
                else:
                    pedido.cliente.email = email
                    pedido.cliente.save()
              
        codigo_transacao = f"{pedido.id}-{datetime.now().timestamp()}"
        pedido.codigo_transacao = codigo_transacao
        pedido.save()

        if erro:
            enderecos = Endereco.objects.filter(cliente=pedido.cliente)
            context = {"erro":erro, "pedido": pedido, "enderecos": enderecos}
            return render(request, "checkout.html", context)
        else:
            pagamento_tipo = dados.get("pagamento")
            # envio de e-mail para PIX ou Entrega/Retirada
            assunto = "Pedido Tudo Mix Site"
            cliente = pedido.cliente
            corpo = (
                f"🔔 Novo pedido via site\n\n"
                f"Número do pedido: {pedido.id}\n"
                f"Valor total: R$ {pedido.preco_total}\n"
                f"Cliente: {cliente.nome} <{cliente.email}>\n"
            )
            destinatarios = ["gustavo@vestelivre.com.br"]

            if pagamento_tipo == "card":
                itens_pedido = ItensPedido.objects.filter(pedido=pedido)
                link = request.build_absolute_uri(reverse('finalizar_pagamento'))
                link_pagamento, id_pagamento = criar_pagamento(itens_pedido, link)
                Pagamento.objects.create(id_pagamento=id_pagamento, pedido=pedido)
                return redirect(link_pagamento)
            
            elif pagamento_tipo == "pix":
                send_mail(assunto, corpo, None, destinatarios, fail_silently=False)
                return redirect('pagamento_pix', id_pedido)
            
            else:
                send_mail(assunto, corpo, None, destinatarios, fail_silently=False)
                return redirect('pagamento_entrega', id_pedido)
    else:    
        return redirect("loja")
    



def finalizar_pagamento(request):
    dados = request.GET.dict()
    status = dados.get("status")
    id_pagamento = dados.get("preference_id")
    if status == "approved":
        pagamento = Pagamento.objects.get(id_pagamento=id_pagamento)
        pagamento.aprovado = True
        pedido = pagamento.pedido
        pedido.finalizado = True
        pedido.data_finalizacao = datetime.now()
        pedido.save()
        pagamento.save()
        enviar_email_compra(pedido)
        if request.user.is_authenticated:
            return redirect('meus_pedidos')
        else:
            return redirect('pedido_aprovado', pedido.id)
    else:
        return redirect('checkout')




def pedido_aprovado(request, id_pedido):
    pedido = Pedido.objects.get(id=id_pedido)
    context = {"pedido": pedido}
    return render(request, 'pedido_aprovado.html', context)




def adicionar_endereco(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            cliente = request.user.cliente
        else:
            if request.COOKIES.get("id_sessao"):
                id_sessao = request.COOKIES.get("id_sessao")
                cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
            else:
                return redirect('loja')
        dados = request.POST.dict()
        endereco = Endereco.objects.create(cliente=cliente, rua=dados.get("rua"), numero=int(dados.get("numero")),
                                           complemento=dados.get("complemento"), cep=dados.get("cep"), bairro=dados.get("bairro"),
                                           cidade=dados.get("cidade"), estado=dados.get("estado"))
        endereco.save()
        return redirect('checkout')
    else:
        context = {}
        return render(request, 'adicionar_endereco.html', context)



@login_required
def minha_conta(request):
    erro = None
    alterado = False
    if request.method == "POST":
        dados = request.POST.dict()
        if "senha_atual" in dados:
            senha_atual = dados.get("senha_atual")
            nova_senha = dados.get("nova_senha")
            nova_senha_confirmacao = dados.get("nova_senha_confirmacao")
            if nova_senha == nova_senha_confirmacao:
                #verificar senha atual está correta
                usuario = authenticate(request, username=request.user.email, password=senha_atual)
                if usuario:
                    usuario.set_password(nova_senha)
                    usuario.save()
                    alterado = True
                else:
                    erro = "senha_incorreta"
            else:
                erro = "senhas_diferentes"
        elif "email" in dados:
            email = dados.get("email")
            nome = dados.get("nome")
            telefone = dados.get("telefone")
            cpf = dados.get("cpf")
            if email != request.user.email:
                usuarios = User.objects.filter(email=email)
                if len(usuarios) > 0:
                    erro = "email_existente"
            if not erro:
                cliente = request.user.cliente
                cliente.email = email
                request.user.email = email
                request.user.username = email
                cliente.nome = nome
                cliente.telefone = telefone
                cliente.cpf = cpf
                cliente.save()
                request.user.save()
                alterado = True
        else:
            erro = "formulario_invalido"
    context = {"erro": erro, "alterado": alterado}
    return render(request, 'usuario/minha_conta.html', context)



@login_required
def meus_pedidos(request):
    cliente = request.user.cliente
    pedidos = Pedido.objects.filter(finalizado=True, cliente=cliente).order_by("-data_finalizacao")
    context = {"pedidos": pedidos}
    return render(request, "usuario/meus_pedidos.html", context)



def fazer_login(request):
    erro = False
    if request.user.is_authenticated:
        return redirect('loja')
    if request.method == "POST":
        dados = request.POST.dict()
        if "email" in dados and "senha" in dados:
            email = dados.get("email")
            senha = dados.get("senha")
            usuario = authenticate(request, username=email, password=senha)
            if usuario:
                login(request, usuario)
                return redirect('loja')
            else:
                erro = True
        else:
            erro = True

    context = {"erro": erro}
    return render(request, 'usuario/login.html', context)



def criar_conta(request):
    erro = None
    if request.user.is_authenticated:
        return redirect('loja')
    if request.method == "POST":
        dados = request.POST.dict()
        if "email" in dados and "senha" in dados and "confirmacao_senha" in dados:
            email = dados.get("email")
            senha = dados.get("senha")
            confirmacao_senha = dados.get("confirmacao_senha")
            try:
                validate_email(email)
            except ValidationError:
                erro = "email_invalido"
            if senha == confirmacao_senha:
                usuario, criado = User.objects.get_or_create(username=email, email=email)
                if not criado:
                    erro = "usuario_existente"
                else:
                    usuario.set_password(senha)
                    usuario.save()
                    # fazer o login
                    usuario = authenticate(request, username=email, password=senha)
                    login(request, usuario)
                    # criar cliente
                    if request.COOKIES.get("id_sessao"):
                        id_sessao = request.COOKIES.get("id_sessao")
                        cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
                    else:
                        cliente, criado = Cliente.objects.get_or_create(email=email)
                    cliente.usuario = usuario
                    cliente.email = email
                    cliente.save()
                    return redirect('loja')
            else:
                erro = "senhas_diferentes"
        else:
            erro = "preenchimento"
    context = {"erro": erro}
    return render(request, 'usuario/criar_conta.html', context)


@login_required
def fazer_logout(request):
    logout(request)
    return redirect('loja')


@login_required
def gerenciar_loja(request):
    if request.user.groups.filter(name="equipe").exists():
        pedidos_finalizados = Pedido.objects.filter(finalizado=True)
        qtde_pedidos = len(pedidos_finalizados)
        faturamento = sum(pedido.preco_total for pedido in pedidos_finalizados)
        qtde_produtos = sum(pedido.quantidade_total for pedido in pedidos_finalizados)
        context = {"qtde_pedidos": qtde_pedidos, "faturamento": faturamento, "qtde_produtos": qtde_produtos}
        return render(request, "interno/gerenciar_loja.html", context)
    else:
        redirect('loja')


@login_required
def exportar_relatorio(request, relatorio):
    if request.user.groups.filter(name="equipe").exists():      
        if relatorio == "pedido":
            informacoes = Pedido.objects.filter(finalizado=True)
        elif relatorio == "cliente":
            informacoes = Cliente.objects.all()
        elif relatorio == "endereco":
            informacoes = Endereco.objects.all()
        return exportar_csv(informacoes)
    else:
        return redirect('gerenciar_loja')
    


def info_empresa(request):
    return render(request, 'institucional/empresa.html')


def info_seguranca(request):
    return render(request, 'institucional/seguranca.html')


def info_envio(request):
    return render(request, 'institucional/envio.html')


def info_troca(request):
    return render(request, 'institucional/troca.html')


def info_politica_privacidade(request):
    return render(request, 'institucional/politica_privacidade.html')




def pagamento_pix(request, id_pedido):
    pedido = get_object_or_404(Pedido, id=id_pedido)
    chave_pix = "gustavomamede@icloud.com"

    pix = generate_simple_pix(
        fullname="TUDO MIX",
        key=chave_pix,
        city="Uberlândia",
        value=float(pedido.preco_total),
        pix_id=str(pedido.id),
        description=f"Pedido #{pedido.id}"
    )

    qr_b64 = pix.toBase64()
    pix_payload = str(pix)
    context = {"pedido": pedido, "chave_pix": chave_pix, "qr_code": qr_b64,  "pix_payload": pix_payload}
    return render(request, "pagamento_pix.html", context)




def pagamento_entrega(request, id_pedido):
    pedido = get_object_or_404(Pedido, id=id_pedido)
    context = {"pedido": pedido}
    return render(request, "pagamento_entrega.html", context)