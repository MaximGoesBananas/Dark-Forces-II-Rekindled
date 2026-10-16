"""Check visible binding labels through the engine's actual string lookup order."""
import os
import tempfile
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1])
source = (root / "src/Main/jkStrings.c").read_text()
tables = []
for filename in ("openjkdf2_i8n.uni", "openjkdf2.uni"):
    content = (root / "resource/ui" / filename).read_text()
    entries = re.findall(r'^\s*"([^"\n]+)"\s+\d+\s+"([^"\n]*)"', content, re.M)
    assert len(entries) == int(re.search(r"MSGS\s+(\d+)", content)[1])
    assert len(dict(entries)) == len(entries)
    tables.append(",".join("{" + json.dumps(k) + "," + json.dumps(v) + "}" for k, v in entries))

code = r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
#define QOL_IMPROVEMENTS
typedef char char16_t;
typedef struct { const char *key; char *value; } Entry;
typedef struct { Entry *entries; size_t count; } stdStrTable;
static char *stdStrTable_GetValue(stdStrTable *t, const char *key) {
    for (size_t i=0; i<t->count; i++)
        if (!strcmp(t->entries[i].key,key)) return t->entries[i].value;
    return NULL;
}
static char *stdStrTable_GetValueOrKey(stdStrTable *t, const char *key) {
    char *value=stdStrTable_GetValue(t,key); return value ? value : (char *)key;
}
static Entry stock[]={{"SELECT1","Fists"}}, overrides[]={OVERRIDES}, extensions[]={EXTENSIONS};
static stdStrTable jkStrings_table={stock,1}, jkCog_strings={0},
    jkStrings_tableExtOver={overrides,sizeof(overrides)/sizeof(*overrides)},
    jkStrings_tableExt={extensions,sizeof(extensions)/sizeof(*extensions)};
'''.replace("OVERRIDES", tables[0]).replace("EXTENSIONS", tables[1])
for name in ("jkStrings_GetUniString", "jkStrings_GetUniStringWithFallback"):
    start = source.index("char16_t* " + name + "(")
    code += source[start:source.index("\n}", start)+2] + "\n"
code += r'''
int main(void) {
    assert(!strcmp(jkStrings_GetUniString("SELECT1"),"Fists / lightsaber"));
    assert(!strcmp(jkStrings_GetUniStringWithFallback("SELECT1"),"Fists / lightsaber"));
    assert(!strcmp(jkStrings_GetUniString("USEVISION"),"Toggle field light"));
    assert(!strcmp(jkStrings_GetUniString("USEBACTA"),"Use Bacta Tank"));
    assert(!strcmp(jkStrings_GetUniString("QUICKLOAD"),"Quick Load"));
}
'''
scratch = Path(os.environ.get("JK_SCRATCH", tempfile.gettempdir())) / "jk-rpg-label-audit"
scratch.mkdir(parents=True, exist_ok=True)
cfile, binary = scratch / "labels.c", scratch / "labels"
try:
    cfile.write_text(code)
    subprocess.run(["cc", "-std=c99", str(cfile), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
finally:
    cfile.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
