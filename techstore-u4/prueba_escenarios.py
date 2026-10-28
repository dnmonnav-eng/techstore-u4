import csv
from decimal import Decimal
from cargar_csv import load_fixture
from app.domain import InvalidOrderTransition, InvalidOrderData, OrderItemLimitExceeded, OrderItem, Money
from app.specifications import get_ten_percent_spec, get_five_percent_spec

print("==================================================")
print("       EJECUTANDO LOS 15 ESCENARIOS (E01 - E15)    ")
print("==================================================")

# Cargar los pedidos frescos desde los fixtures
orders = load_fixture()

spec_10 = get_ten_percent_spec()
spec_5 = get_five_percent_spec()

# Leer el archivo de escenarios CSV
with open("datos/escenarios.csv", mode="r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)
    
    for row in reader:
        caso_id = row["caso_id"]
        pedido_id = row["pedido_id"]
        accion = row["accion"]
        objetivo = row["objetivo"]
        pista = row["pista"]
        
        print(f"\n[{caso_id}] Pedido: {pedido_id} | Acción: {accion}")
        print(f"    -> Objetivo: {objetivo} ({pista})")
        
        order = orders.get(pedido_id)
        if not order:
            print(f"    Pedido {pedido_id} no encontrado en memoria.")
            continue
            
        try:
            # 1. Casos de evaluación de descuentos (E01, E02, E04, E05, E09, E10)
            if "evaluar_descuento" in accion:
                if "10%" in objetivo:
                    aplica = spec_10.is_satisfied_by(order)
                    print(f"    Resultado: Descuento 10% -> {'APLICA' if aplica else 'NO APLICA'}")
                elif "5%" in objetivo:
                    aplica = spec_5.is_satisfied_by(order)
                    print(f"    Resultado: Descuento 5% -> {'APLICA' if aplica else 'NO APLICA'}")
                else:
                    t10 = spec_10.is_satisfied_by(order)
                    t5 = spec_5.is_satisfied_by(order)
                    print(f"    Resultado: 10%({t10}), 5%({t5}) -> Esperado 0%")

            # 2. Casos de confirmación simple o rechazos (E03, E06, E07)
            elif accion == "confirmar":
                order.confirm()
                print(f"    Éxito: Pedido confirmado correctamente. Estado: {order.status.value}")

            # 3. Casos de agregar ítems con exceso de límite (E08)
            elif "agregar" in accion:
                order.add_item(OrderItem("SKU003", 21, Money(Decimal("100"))))
                print("    Ítems agregados con éxito")

            # 4. Casos combinados de la máquina de estados (E11 a E15)
            elif "confirmar y enviar sin guia" in accion or caso_id == "E11":
                order.confirm()
                order.ship("") # Esto debe fallar por guía vacía
                
            elif "confirmar dos veces" in accion or caso_id == "E12":
                order.confirm()
                order.confirm() # Segunda vez debe fallar
                
            elif "confirmar, enviar y cancelar" in accion or caso_id == "E13":
                order.confirm()
                order.ship("GUIA-999")
                order.cancel("Motivo de prueba") # Debe fallar porque ya está shipped
                
            elif "confirmar, enviar y devolver" in accion or caso_id == "E14":
                order.confirm()
                order.ship("GUIA-999")
                order.return_order()
                print(f"    Flujo exitoso. Estado final: {order.status.value}")
                
            elif "confirmar, enviar y entregar" in accion or caso_id == "E15":
                order.confirm()
                order.ship("GUIA-999")
                order.deliver()
                print(f"    Flujo exitoso. Estado final: {order.status.value}")
                
            else:
                print(f"    Acción no automatizada específicamente: {accion}")

        except (InvalidOrderTransition, InvalidOrderData, OrderItemLimitExceeded) as e:
            print(f"    Excepción capturada correctamente (Comportamiento esperado): {type(e).__name__} -> {e}")
        except Exception as ex:
            print(f"    Error inesperado: {ex}")

print("\n==================================================")
print("       PRUEBA DE LOS 15 ESCENARIOS FINALIZADA      ")
print("==================================================")