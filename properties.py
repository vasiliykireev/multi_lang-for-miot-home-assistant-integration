#!/usr/bin/env python3
"""
Скрипт для извлечения описаний сервисов/свойств/действий/событий из MIoT JSON-спецификации
и подготовки структуры для lang-файла интеграции.

Пример использования:
  python3 properties.py urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1
или
  python3 properties.py --urn urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1

Опционально можно указать --output <file> для сохранения результата.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def fetch_instance(urn: str) -> Dict[str, Any]:
    url = f"http://miot-spec.org/miot-spec-v2/instance?type={urn}"
    try:
        with urllib.request.urlopen(url) as resp:
            status = resp.getcode()
            if status != 200:
                raise urllib.error.HTTPError(url, status, f"HTTP {status}", hdrs=None, fp=None)
            data = resp.read()
            return json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Ошибка HTTP при запросе {url}: {getattr(e, 'code', str(e))}")
        raise
    except urllib.error.URLError as e:
        print(f"Ошибка сети при запросе {url}: {e}")
        raise


def extract_description(obj: Any) -> str:
    """Пытаемся извлечь человекочитаемое описание из объекта спецификации."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        try:
            return str(obj)
        except Exception:
            return ""

    # Частые поля с описанием
    for key in ("description", "name", "title", "desc", "display-name"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # Иногда описание может быть вложенным (на языке и т.д.)
    for key in ("description",):
        v = obj.get(key)
        if isinstance(v, dict):
            # попробуем взять любую строковую запись
            for sub in ("en", "zh", "zh-CN", "cn", "default"):
                if sub in v and isinstance(v[sub], str) and v[sub].strip():
                    return v[sub].strip()
            # fallback: first string value
            for subk, subv in v.items():
                if isinstance(subv, str) and subv.strip():
                    return subv.strip()

    return ""


def format_id(val: Any) -> str:
    """Форматируем идентификатор как 3-значный строковый номер, если это число.
    Иначе возвращаем строку без изменений (обрезая пробелы).
    """
    if val is None:
        return "000"
    if isinstance(val, int):
        return f"{val:03d}"
    try:
        s = str(val).strip()
        if s.isdigit():
            return f"{int(s):03d}"
        return s
    except Exception:
        return str(val)


def find_services(root: Any) -> List[Dict[str, Any]]:
    """Ищем список сервисов в структуре JSON.
    Обычный путь: root['services']
    Иначе рекурсивно ищем список элементов, у которых есть ключ 'siid' или 'iid'.
    """
    if isinstance(root, dict):
        for key in ("services", "service", "specServices"):
            if key in root and isinstance(root[key], list):
                return root[key]

    # рекурсивный поиск
    found = []

    def _walk(obj: Any):
        if isinstance(obj, dict):
            # если это список сервисов
            for k, v in obj.items():
                if isinstance(v, list):
                    for el in v:
                        if isinstance(el, dict) and ("siid" in el or "iid" in el):
                            found.extend(v)
                            return True
                if isinstance(v, (dict, list)):
                    if _walk(v):
                        return True
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict) and ("siid" in item or "iid" in item):
                    found.extend(obj)
                    return True
                if isinstance(item, (dict, list)):
                    if _walk(item):
                        return True
        return False

    _walk(root)
    return found


def build_mapping(data: Dict[str, Any], urn: str, lang: str = "ru") -> Dict[str, Dict[str, str]]:
    services = find_services(data)
    mapping: Dict[str, str] = {}

    for svc in services:
        siid = format_id(svc.get("siid") or svc.get("iid") or svc.get("id"))
        svc_desc = extract_description(svc) or ""
        if svc_desc:
            mapping[f"service:{siid}"] = svc_desc

        # properties
        for prop in svc.get("properties", []) if isinstance(svc.get("properties", []), list) else []:
            piid = format_id(prop.get("piid") or prop.get("iid") or prop.get("id"))
            pdesc = extract_description(prop) or ""
            if pdesc:
                mapping[f"service:{siid}:property:{piid}"] = pdesc

            # value list
            val_list = None
            for vn in ("value-list", "value_list", "valueList", "enum", "value list", "values"):
                if vn in prop:
                    val_list = prop[vn]
                    break
            if isinstance(val_list, list):
                for idx, entry in enumerate(val_list):
                    # entry может быть строкой или объектом
                    if isinstance(entry, str):
                        vdesc = entry.strip()
                    elif isinstance(entry, dict):
                        vdesc = extract_description(entry) or (entry.get("value") or entry.get("name") or "")
                        if isinstance(vdesc, str):
                            vdesc = vdesc.strip()
                    else:
                        vdesc = str(entry)
                    if vdesc:
                        mapping[f"service:{siid}:property:{piid}:valuelist:{idx:03d}"] = vdesc

        # actions
        for act in svc.get("actions", []) if isinstance(svc.get("actions", []), list) else []:
            aiid = format_id(act.get("aiid") or act.get("iid") or act.get("id"))
            adesc = extract_description(act) or ""
            if adesc:
                mapping[f"service:{siid}:action:{aiid}"] = adesc

        # events
        for ev in svc.get("events", []) if isinstance(svc.get("events", []), list) else []:
            eiid = format_id(ev.get("eiid") or ev.get("iid") or ev.get("id"))
            edesc = extract_description(ev) or ""
            if edesc:
                mapping[f"service:{siid}:event:{eiid}"] = edesc

    # Sort mapping keys for deterministic output
    sorted_mapping = {k: mapping[k] for k in sorted(mapping.keys(), key=lambda x: (int(x.split(":")[1]) if x.split(":")[1].isdigit() else x))}
    return {urn: {lang: sorted_mapping}}


def normalize_urn(urn: str) -> str:
    """Убирает конечный суффикс ":<digits>" из URN, если он есть.

    Примеры:
      urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1 -> urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1
    """
    if not isinstance(urn, str):
        return urn
    parts = urn.rsplit(":", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return urn


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Собирает описания свойств MIoT-устройства для lang-файла.")
    p.add_argument("urn", nargs="?", help="URN устройства, например: urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1")
    p.add_argument("--output", "-o", help="Если указано, сохраняет результат в файл (JSON). По умолчанию будет использовано '<urn>.json'")
    p.add_argument("--file", "-f", help="Использовать локальный файл JSON спецификации вместо запроса по сети")
    p.add_argument("--lang", "-l", default="ru", help="Ключ языка для вывода (по умолчанию: ru)")
    args = p.parse_args(argv)

    if not args.urn:
        p.print_usage()
        print("Ошибка: необходимо указать URN устройства.")
        return 2

    urn = args.urn

    data = None
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as e:
            print(f"Не удалось прочитать файл {args.file}: {e}")
            return 5
    else:
        try:
            data = fetch_instance(urn)
        except Exception:
            print("Не удалось получить спецификацию устройства. Проверьте URN и сетевое соединение.")
            return 3

    norm_urn = normalize_urn(urn)
    result = build_mapping(data, norm_urn, lang=args.lang)

    print("Данные: description")
    print(json.dumps(result, ensure_ascii=False, indent=4, sort_keys=False))

    default_filename = f"{norm_urn}.json"
    output_path = args.output if args.output else default_filename
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"Сохранено в {output_path}")
    except Exception as e:
        print(f"Не удалось сохранить файл {output_path}: {e}")
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
