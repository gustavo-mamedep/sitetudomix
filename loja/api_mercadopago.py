import mercadopago

public_key = "APP_USR-4f1ed198-04be-4a9b-9285-4c9f420d26fc"
token = "APP_USR-5139457133130532-071405-b03733da9a87c40a2f0e66588abf9b61-157469376"

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
        "auto_return": "all",
        "back_urls":{
            "success": link,
            "pending": link,
            "failure": link,
        }
    }
    resposta = sdk.preference().create(preference_data)
    link_pagamento = resposta["response"]["init_point"]
    id_pagamento = resposta["response"]["id"]
    return link_pagamento, id_pagamento