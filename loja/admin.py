from django.contrib import admin
from .models import *

admin.site.register(Cliente)
admin.site.register(Categoria)
admin.site.register(Subcategoria)
admin.site.register(Endereco)
admin.site.register(Pedido)
admin.site.register(ItensPedido)
admin.site.register(Banner)
admin.site.register(Cor)
admin.site.register(Pagamento)

class ProdutoImagemInline(admin.TabularInline):
    model = ProdutoImagem
    extra = 1
    fields = ('ordem', 'imagem')

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'referencia', 'preco', 'ativo')
    search_fields = ('nome', 'referencia')  # <-- adiciona o campo de busca
    inlines = [ProdutoImagemInline]


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'cor', 'quantidade')
    search_fields = ('produto__nome', 'produto__referencia')
    autocomplete_fields = ('produto',)