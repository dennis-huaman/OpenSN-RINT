import json
import string

def calculate_tle_checksum(line: str) -> int:
    """
    Calcula el dígito de verificación (checksum) para una línea TLE.
    Suma todos los dígitos, asigna +1 a los signos menos, y luego toma el módulo 10.
    """
    checksum = 0
    # Procesar solo los primeros 68 caracteres de la línea
    for i in range(min(68, len(line))):
        c = line[i]
        if c.isdigit():
            checksum += int(c)
        elif c == '-':
            checksum += 1
        # Los espacios, puntos, signos más y letras se ignoran (suman 0)
    return checksum % 10

def fix_tle_lines(line_1: str, line_2: str):
    """
    Corrige los checksums de las líneas TLE y devuelve líneas nuevas.
    """
    # Asegurar que las líneas tengan 69 caracteres (68 datos + 1 checksum)
    # Eliminar el checksum antiguo si existe
    line_1_base = line_1[:-1].strip() if line_1 and len(line_1) >= 69 else line_1.strip()
    line_2_base = line_2[:-1].strip() if line_2 and len(line_2) >= 69 else line_2.strip()

    # Calcular nuevos checksums
    cs1 = calculate_tle_checksum(line_1_base)
    cs2 = calculate_tle_checksum(line_2_base)

    # Añadir los nuevos checksums
    return line_1_base + str(cs1), line_2_base + str(cs2)

def process_tle_in_json(input_file: str, output_file: str):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for instance in data['instances']:
        extra = instance.get('extra', {})
        if 'TLE_1' in extra and 'TLE_2' in extra:
            original_1 = extra['TLE_1']
            original_2 = extra['TLE_2']
            fixed_1, fixed_2 = fix_tle_lines(original_1, original_2)
            
            if fixed_1 != original_1 or fixed_2 != original_2:
                print(f"Corrigiendo {extra.get('TLE_0', 'satélite sin nombre')}:")
                print(f"  Línea 1 antes: {original_1}")
                print(f"  Línea 1 ahora: {fixed_1}")
                print(f"  Línea 2 antes: {original_2}")
                print(f"  Línea 2 ahora: {fixed_2}")
                extra['TLE_1'] = fixed_1
                extra['TLE_2'] = fixed_2
            else:
                print(f"✓ {extra.get('TLE_0', 'satélite sin nombre')} ya tiene checksums válidos.")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\n✨ Archivo corregido guardado como: {output_file}")

if __name__ == "__main__":
    # --- IMPORTANTE: Cambia estos nombres si es necesario ---
    input_filename = "topology_config_2_4.json"
    output_filename = "topology_config_2_4_fixed.json"
    # -------------------------------------------------------
    process_tle_in_json(input_filename, output_filename)