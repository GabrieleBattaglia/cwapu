import ast
import os

# --- Configurazione ---
# Modifica questi valori per processare file diversi
SOURCE_FILE = 'cwapu.py'
OUTPUT_FILE = 'cwapu_new.py'

# Non modificare questi se non sai cosa stai facendo
TRANSLATION_FILE = 'translate'
TRANSLATION_DICT_NAME = 'translations'
OLD_FUNCTION_NAME = 'Trnsl'


class InternationalizationTransformer(ast.NodeTransformer):
    """
    Esegue un doppio refactoring per l'internazionalizzazione:
    1. Sostituisce le chiamate a Trnsl("key") con _("testo italiano").
    2. Converte le f-string in chiamate _("template {}").format(args).
    """
    def __init__(self, translation_map):
        self.translation_map = translation_map
        self.trnsl_replacements = 0
        self.fstring_replacements = 0

    def visit_Call(self, node):
        # PRIMA TRASFORMAZIONE: Gestisce Trnsl("key")
        if isinstance(node.func, ast.Name) and node.func.id == OLD_FUNCTION_NAME:
            if len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                key = node.args[0].value
                
                if 'it' in self.translation_map and key in self.translation_map['it']:
                    italian_string = self.translation_map['it'][key]
                    new_node = ast.Call(
                        func=ast.Name(id='_', ctx=ast.Load()),
                        args=[ast.Constant(value=italian_string)],
                        keywords=[]
                    )
                    self.trnsl_replacements += 1
                    print(f"Sostituito Trnsl: {OLD_FUNCTION_NAME}('{key}') -> _('{italian_string}')")
                    ast.copy_location(new_node, node)
                    ast.fix_missing_locations(new_node)
                    return new_node
                else:
                    print(f"ATTENZIONE (Trnsl): Chiave '{key}' non trovata nel dizionario italiano.")
            else:
                print(f"ATTENZIONE (Trnsl): Chiamata non gestita: {ast.unparse(node)}")

        return self.generic_visit(node)

    def visit_JoinedStr(self, node):
        # SECONDA TRASFORMAZIONE: Gestisce le f-string
        template_parts = []
        format_args = []

        for value_node in node.values:
            if isinstance(value_node, ast.Constant):
                # Le parentesi graffe letterali in una f-string vanno escapate
                template_parts.append(value_node.value.replace("{", "{{").replace("}", "}}"))
            elif isinstance(value_node, ast.FormattedValue):
                # Estrae l'espressione da formattare
                format_args.append(value_node.value)
                
                # Ricostruisce il placeholder, preservando flag di conversione e formattazione
                conversion = f"!{chr(value_node.conversion)}" if value_node.conversion != -1 else ""
                format_spec_str = ast.unparse(value_node.format_spec) if value_node.format_spec else ""
                placeholder = f"{{{conversion}{':' + format_spec_str if format_spec_str else ''}}}"
                template_parts.append(placeholder)
        
        template_string = "".join(template_parts)

        # Costruisce il nodo _("template")
        gettext_call = ast.Call(
            func=ast.Name(id='_', ctx=ast.Load()),
            args=[ast.Constant(value=template_string)],
            keywords=[]
        )
        
        # Se non ci sono argomenti, restituisce solo _("stringa")
        if not format_args:
            return gettext_call

        # Altrimenti, costruisce il nodo completo _("...").format(...)
        format_call_node = ast.Call(
            func=ast.Attribute(
                value=gettext_call,
                attr='format',
                ctx=ast.Load()
            ),
            args=format_args,
            keywords=[]
        )
        
        self.fstring_replacements += 1
        print(f"Trasformata f-string in: _(\"{template_string}\").format(...)")
        
        ast.copy_location(format_call_node, node)
        ast.fix_missing_locations(format_call_node)
        return format_call_node

def main():
    print(f"--- AVVIO REFACTORING SU {SOURCE_FILE} ---")

    try:
        translation_module = __import__(TRANSLATION_FILE)
        translation_dict = getattr(translation_module, TRANSLATION_DICT_NAME)
        print(f"Dizionario '{TRANSLATION_DICT_NAME}' caricato con successo.")
    except (ImportError, AttributeError) as e:
        print(f"ERRORE: Impossibile caricare il dizionario. Dettagli: {e}")
        return

    try:
        with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"ERRORE: File sorgente '{SOURCE_FILE}' non trovato.")
        return
        
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        print(f"ERRORE: Impossibile effettuare il parsing di '{SOURCE_FILE}'. Dettagli: {e}")
        return

    transformer = InternationalizationTransformer(translation_dict)
    new_tree = transformer.visit(tree)
    
    new_tree.body = [n for n in new_tree.body if not (isinstance(n, ast.Import) and any(alias.name == TRANSLATION_FILE for alias in n.names))]
    new_tree.body = [n for n in new_tree.body if not (isinstance(n, ast.ImportFrom) and n.module == TRANSLATION_FILE)]

    try:
        new_code = ast.unparse(new_tree)
    except AttributeError:
        print("ERRORE: `ast.unparse` non disponibile (richiesto Python 3.9+).")
        return

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(new_code)

    print("\n--- REFACTORING COMPLETATO ---")
    print(f"File modificato salvato come: '{OUTPUT_FILE}'")
    print(f"Sostituzioni di Trnsl(...): {transformer.trnsl_replacements}")
    print(f"Trasformazioni di f-string: {transformer.fstring_replacements}")

if __name__ == '__main__':
    main()