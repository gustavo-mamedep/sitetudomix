from .models import Pedido, ItensPedido, Cliente, Categoria, Subcategoria

def carrinho(request):
    quantidade_produtos_carrinho = 0
    if request.user.is_authenticated:
        cliente, criado = Cliente.objects.get_or_create(usuario=request.user)
    else:
        if request.COOKIES.get("id_sessao"):
            id_sessao = request.COOKIES.get("id_sessao")
            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
        else:
            return {"quantidade_produtos_carrinho": quantidade_produtos_carrinho}
    pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
    itens_pedido = ItensPedido.objects.filter(pedido=pedido)
    for item in itens_pedido:
        quantidade_produtos_carrinho += item.quantidade
    return {"quantidade_produtos_carrinho": quantidade_produtos_carrinho}


def categorias_subcategorias(request):
    # Busca cada categoria já com suas subcategorias num único JOIN
    categorias_navegacao = (Categoria.objects.prefetch_related('subcategorias').all())
    return {"categorias_navegacao": categorias_navegacao,}


def faz_parte_equipe(request):
    equipe = False
    if request.user.is_authenticated:
        if request.user.groups.filter(name="equipe").exists():
            equipe = True
    return {"equipe": equipe}
            