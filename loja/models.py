from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField

# Create your models here.

class Cliente(models.Model):
    nome = models.CharField(max_length=200, null=True, blank=True)
    email = models.CharField(max_length=200, null=True, blank=True)
    cpf = models.CharField(max_length=20, null=True, blank=True)
    telefone = models.CharField(max_length=200, null=True, blank=True)
    id_sessao = models.CharField(max_length=200, null=True, blank=True)
    usuario = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.nome} - {self.email}'



class Categoria(models.Model):
    nome = models.CharField(max_length=200, null=True, blank=True)
    slug = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(self.nome)




class Subcategoria(models.Model):
    categoria = models.ForeignKey(Categoria, related_name='subcategorias', on_delete=models.CASCADE)
    nome = models.CharField(max_length=200, null=True, blank=True)
    slug = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return str(self.nome)




class Produto(models.Model):
    nome = models.CharField(max_length=200, null=True, blank=True)
    referencia = models.CharField(max_length=200, null=True, blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    categoria = models.ForeignKey(Categoria, null=True, blank=True, on_delete=models.SET_NULL)
    subcategoria = models.ForeignKey(Subcategoria, null=True, blank=True, on_delete=models.SET_NULL)
    descricao = models.TextField(null=True, blank=True, default="")

    def __str__(self):
        return f"Nome: {self.nome} - Ref.: {self.referencia} - Preço: R$ {self.preco} - Catedoria: {self.categoria} - {self.subcategoria}"

    def total_vendas(self):
        itens = ItensPedido.objects.filter(pedido__finalizado=True, item_estoque__produto=self.id)
        total = sum([item.quantidade for item in itens])
        return total




class ProdutoImagem(models.Model):
    produto = models.ForeignKey(Produto, related_name='imagens', on_delete=models.CASCADE)
    imagem = CloudinaryField('image', folder='produtos/')
    ordem = models.PositiveIntegerField(default=0, help_text="Define a ordem de exibição das imagens")

    class Meta:
        ordering = ['ordem']

    def __str__(self):
        return f"{self.produto.nome} – Foto #{self.ordem}"



class Cor(models.Model):
    nome = models.CharField(max_length=200, null=True, blank=True)
    codigo = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(self.nome)




class ItemEstoque(models.Model):
    produto = models.ForeignKey(Produto, null=True, blank=True, on_delete=models.SET_NULL)
    cor = models.ForeignKey(Cor, null=True, blank=True, on_delete=models.SET_NULL)
    quantidade = models.IntegerField(default=0)

    class Meta:
        unique_together = ('produto', 'cor')

    def __str__(self):
        return f"{self.produto.nome} - Cor: {self.cor.nome} - Qtde: {self.quantidade}"





class Endereco(models.Model):
    rua = models.CharField(max_length=400, null=True, blank=True)
    numero = models.IntegerField(default=0)
    complemento = models.CharField(max_length=200, null=True, blank=True)
    cep = models.CharField(max_length=20, null=True, blank=True)
    bairro = models.CharField(max_length=200, null=True, blank=True)
    cidade = models.CharField(max_length=200, null=True, blank=True)
    estado = models.CharField(max_length=200, null=True, blank=True)
    cliente =  models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.cliente.nome} - {self.rua}, {self.numero} - {self.complemento} - {self.bairro} - {self.cidade} - {self.estado}"



class Pedido(models.Model):
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.SET_NULL)
    finalizado = models.BooleanField(default=False)
    codigo_transacao = models.CharField(max_length=200, null=True, blank=True)
    endereco = models.ForeignKey(Endereco, null=True, blank=True, on_delete=models.SET_NULL)
    data_finalizacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Cliente: {self.cliente} - Pedido número: {self.id} - Finalizado: {self.finalizado}'

    @property
    def quantidade_total(self):
        itens_pedido = ItensPedido.objects.filter(pedido_id=self.id)
        quantidade = sum([item.quantidade for item in itens_pedido])
        return quantidade

    @property
    def preco_total(self):
        itens_pedido = ItensPedido.objects.filter(pedido_id=self.id)
        preco = sum([item.preco_total for item in itens_pedido])
        return preco
    
    @property
    def itens(self):
        itens_pedido = ItensPedido.objects.filter(pedido_id=self.id)
        return itens_pedido


class ItensPedido(models.Model):
    item_estoque = models.ForeignKey(ItemEstoque, null=True, blank=True, on_delete=models.SET_NULL)
    quantidade = models.IntegerField(default=0)
    pedido = models.ForeignKey(Pedido, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f'Id Pedido: {self.pedido.id} - Produto: {self.item_estoque.produto.nome} - {self.item_estoque.cor.nome}'
    @property
    def preco_total(self):
        return self.quantidade * self.item_estoque.produto.preco





class Banner(models.Model):
    imagem = CloudinaryField('image', folder='banners/')
    link_destino = models.CharField(max_length=255, blank=True)
    ativo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.link_destino} - Ativo: {self.ativo}"




class Pagamento(models.Model):
    id_pagamento = models.CharField(max_length=400)
    pedido = models.ForeignKey(Pedido, null=True, blank=True, on_delete=models.SET_NULL)
    aprovado = models.BooleanField(default=False)