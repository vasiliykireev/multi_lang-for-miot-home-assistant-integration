# properties.py — генератор данных для lang-файла MIoT-интеграции Xiaomi с Home Assistant

Скрипт `properties.py` извлекает описания сервисов, свойств, действий и событий из MIoT JSON-спецификации устройства и формирует структуру для `lang`-файла переводов в Home Assistant.

Подробнее: https://github.com/XiaoMi/ha_xiaomi_home/?tab=readme-ov-file#multiple-language-support

## Что делает
- Берёт URN устройства MIoT и запрашивает спецификацию по URL:
  `http://miot-spec.org/miot-spec-v2/instance?type=<URN>`
- Извлекает описания для:
  - service:<siid>
  - service:<siid>:property:<piid>
  - service:<siid>:property:<piid>:valuelist:<index>
  - service:<siid>:event:<eiid>
  - service:<siid>:action:<aiid>
- Формирует JSON в виде:

```json
{
  "<URN>": {
    "<lang>": {
      "service:002": "...",
      "service:002:property:001": "...",
      "service:002:property:001:valuelist:000": "...",
      "service:002:action:002": "...",
      "service:005:event:001": "..."
    }
  }
}
```

## Как запустить
Требуется Python 3.

Примеры:

- Получить спецификацию по сети и вывести результат в консоль (пример URN, использованный при разработке):

```bash
python3 properties.py 'urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1'
```

- Сохранить результат в файл `result.json` (или указать явный путь):

```bash
python3 properties.py 'urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1' --output result.json
```

- Использовать локальную копию спецификации (удобно для разработки):

```bash
python3 properties.py 'urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1' --file path/to/local.json --output result.json
```

- Указать язык-ключ (по умолчанию `ru`):

```bash
python3 properties.py 'urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1' --lang en
```

Примечание: если опция `--output` не указана, результат будет сохранён в файл с именем `<URN>.json`, например:

```bash
# если не указать --output
python3 properties.py 'urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1'
# сохранит в файл 'urn:miot-spec-v2:device:health-pot:0000A051:chunmi-a1:1.json'
```

## Опции
- `--file` / `-f` — использовать локальный JSON-файл вместо сетевого запроса.
- `--output` / `-o` — сохранить результат в указанный файл.
- `--lang` / `-l` — ключ языка в результирующей структуре (по умолчанию `ru`).

## Замечания и отладка
- Если URL спецификации возвращает код отличной от 200, скрипт сообщит об ошибке.
- Поля в JSON-спецификации могут отличаться по названиям (value-list / valueList / enum и т.д.). Скрипт пытается учесть несколько распространённых вариантов.
- Для нестандартных или сильно вложенных спецификаций может потребоваться ручная корректировка парсера.

## Возможные улучшения
- Поддержка выбора приоритета локализации (например, выбирать `zh`/`en` описание, если есть).
- Более точная сортировка и форматирование ключей (service → property → valuelist).
- Unit-тесты для разных форматов спецификаций.

## Пример результата
Файл `result.json` (фрагмент) будет выглядеть примерно так:

```json
{
  "urn:miot-spec-v2:device:air-conditioner:0000A004:xiaomi-m6:1": {
    "ru": {
      "service:001": "Device Information",
      "service:001:property:001": "Device Manufacturer",
      "service:002": "Air Conditioner",
      "service:002:property:002": "Mode",
      "service:002:property:002:valuelist:000": "Cool",
      "service:002:property:002:valuelist:001": "Dry"
    }
  }
}
```
