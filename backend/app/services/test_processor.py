"""
Teste do pipeline de conversão BRL
Execute: python -m app.services.test_processor
"""
import pandas as pd
import os
import sys

# Import do mesmo diretório
from app.services.xlsx_processor import _to_brl_number

def test_conversion():
    """Testa conversão de valores BRL"""
    print("\n" + "="*60)
    print("🧪 TESTE DE CONVERSÃO BRL")
    print("="*60)
    
    # Simula valores do Excel
    test_data = pd.DataFrame({
        "Receita por produtos (BRL)": [
            "R$ 1.234,56",
            "R$ 234,56",
            "R$ 56.789,12",
            "-118,83",
            "699",
            "R$ 0,00",
            "",
        ]
    })
    
    print("\n1️⃣ VALORES ORIGINAIS (strings):")
    for i, val in enumerate(test_data["Receita por produtos (BRL)"], 1):
        print(f"   {i}. '{val}'")
    
    # Converte
    converted = _to_brl_number(test_data["Receita por produtos (BRL)"])
    test_data["Receita por produtos (BRL)"] = converted
    
    print("\n2️⃣ VALORES CONVERTIDOS (float):")
    for i, val in enumerate(test_data["Receita por produtos (BRL)"], 1):
        print(f"   {i}. {val:.2f}")
    
    # Soma
    total = test_data["Receita por produtos (BRL)"].sum()
    expected = 1234.56 + 234.56 + 56789.12 - 118.83 + 699
    
    print(f"\n3️⃣ SOMAS:")
    print(f"   Calculada: R$ {total:,.2f}")
    print(f"   Esperada:  R$ {expected:,.2f}")
    print(f"   Diferença: R$ {abs(total - expected):.2f}")
    
    # Valida
    if abs(total - expected) < 0.01:
        print("\n✅ CONVERSÃO OK!")
        return True
    else:
        print("\n❌ CONVERSÃO FALHOU!")
        return False


def test_parquet_persistence():
    """Testa se valores são mantidos após salvar/carregar Parquet"""
    print("\n" + "="*60)
    print("🧪 TESTE DE PERSISTÊNCIA PARQUET")
    print("="*60)
    
    # Cria DataFrame de teste
    test_data = pd.DataFrame({
        "Receita por produtos (BRL)": [
            "R$ 1.234,56",
            "R$ 234,56",
        ]
    })
    
    # Converte
    test_data["Receita por produtos (BRL)"] = _to_brl_number(
        test_data["Receita por produtos (BRL)"]
    )
    
    total_before = test_data["Receita por produtos (BRL)"].sum()
    print(f"\n1️⃣ ANTES de salvar Parquet:")
    print(f"   Valores: {test_data['Receita por produtos (BRL)'].tolist()}")
    print(f"   Soma: R$ {total_before:,.2f}")
    print(f"   Tipo: {test_data['Receita por produtos (BRL)'].dtype}")
    
    # Salva Parquet
    test_path = "/tmp/test_parquet.parquet"
    test_data.to_parquet(test_path, index=False)
    print(f"\n💾 Salvo em: {test_path}")
    
    # Recarrega
    df_loaded = pd.read_parquet(test_path)
    total_after = df_loaded["Receita por produtos (BRL)"].sum()
    
    print(f"\n2️⃣ DEPOIS de carregar Parquet:")
    print(f"   Valores: {df_loaded['Receita por produtos (BRL)'].tolist()}")
    print(f"   Soma: R$ {total_after:,.2f}")
    print(f"   Tipo: {df_loaded['Receita por produtos (BRL)'].dtype}")
    
    # Valida
    if abs(total_before - total_after) < 0.01:
        print("\n✅ PERSISTÊNCIA OK!")
        success = True
    else:
        print("\n❌ PERSISTÊNCIA FALHOU!")
        success = False
    
    # Limpa
    os.remove(test_path)
    print(f"\n🧹 Arquivo {test_path} removido")
    
    return success


def test_real_world_values():
    """Testa com valores mais realistas"""
    print("\n" + "="*60)
    print("🧪 TESTE COM VALORES REAIS")
    print("="*60)
    
    # Valores típicos do Mercado Livre
    test_data = pd.DataFrame({
        "col1": [
            "R$ 12.345,67",    # Receita alta
            "R$ 890,12",       # Receita média
            "-45,30",          # Taxa (negativa)
            "R$ 1.500,00",     # Receita redonda
            "R$ 0,99",         # Valor pequeno
        ]
    })
    
    print("\n1️⃣ Valores de teste:")
    for val in test_data["col1"]:
        print(f"   '{val}'")
    
    # Converte
    converted = _to_brl_number(test_data["col1"])
    
    print("\n2️⃣ Valores convertidos:")
    for val in converted:
        print(f"   {val:.2f}")
    
    # Valida valores específicos
    expected_values = [12345.67, 890.12, -45.30, 1500.00, 0.99]
    
    print("\n3️⃣ Validação individual:")
    all_ok = True
    for i, (result, expected) in enumerate(zip(converted, expected_values), 1):
        diff = abs(result - expected)
        status = "✅" if diff < 0.01 else "❌"
        print(f"   {status} Valor {i}: {result:.2f} (esperado: {expected:.2f}, diff: {diff:.2f})")
        if diff >= 0.01:
            all_ok = False
    
    if all_ok:
        print("\n✅ TODOS OS VALORES OK!")
    else:
        print("\n❌ ALGUNS VALORES INCORRETOS!")
    
    return all_ok


if __name__ == "__main__":
    print("\n" + "🚀 INICIANDO TESTES" + "\n")
    
    results = []
    
    # Executa testes
    results.append(("Conversão BRL", test_conversion()))
    results.append(("Persistência Parquet", test_parquet_persistence()))
    results.append(("Valores Reais", test_real_world_values()))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{status} - {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        sys.exit(0)
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM!")
        sys.exit(1)