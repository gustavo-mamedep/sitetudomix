import mercadopago

public_key = "APP_USR-01ab7896-7c07-4cfd-9475-86602c135c14"
token = "APP_USR-7267787165031172-071406-dd28b44da3f22fedca132714fccad6ba-2559625566"

def criar_pagamento(itens_pedido, link):
    # SDK do Mercado Pago
    sdk = mercadopago.SDK(token)
    itens = []
    for item in itens_pedido:
        quantidade = int(item.quantidade)
        nome_produto = item.item_estoque.produto.nome
        preco_unitario = float(item.item_estoque.produto.preco)
        itens.append({
            "title": nome_produto,
            "quantity": quantidade,
            "unit_price": preco_unitario,
        })

    preference_data = {
        "items": itens,
        # "auto_return": "all",
        # "back_urls":{
        #     "success": link,
        #     "pending": link,
        #     "failure": link,
        # }
    }
    resposta = sdk.preference().create(preference_data)
    link_pagamento = resposta["response"]["init_point"]
    id_pagamento = resposta["response"]["id"]
    return link_pagamento, id_pagamento