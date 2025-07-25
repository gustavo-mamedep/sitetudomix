from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Cliente)
admin.site.register(Categoria)
admin.site.register(Subcategoria)
admin.site.register(ItemEstoque)
admin.site.register(Endereco)
admin.site.register(Pedido)
admin.site.register(ItensPedido)
admin.site.register(Banner)
admin.site.register(Cor)
admin.site.register(Pagamento)

class ProdutoImagemInline(admin.TabularInline):
    model = ProdutoImagem
    extra = 2
    fields = ('ordem','imagem')

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome','referencia','preco','ativo')
    inlines = [ProdutoImagemInline]