# ⭐ Сокрытие кода. Folding. VSCode Расширение Explicit Folding

PAGE Для меня это «game-changer»

<hr>

## Показываю

<!-- [[[cog
from pathlib import Path
print()
for x in Path("docs/assets").glob("useful_03_*.png"):
  print("![](/{})".format(x.as_posix()))
  print("<br>")
  print("<br>")
print()
cog]]] -->

![](/docs/assets/useful_03_2.png)
<br>
<br>
![](/docs/assets/useful_03_3.png)
<br>
<br>
![](/docs/assets/useful_03_Code_2026-03-22_22.22.44.png)
<br>
<br>
![](/docs/assets/useful_03_Code_2026-03-22_22.22.51.png)
<br>
<br>
![](/docs/assets/useful_03_Code_2026-03-27_09.03.20.png)
<br>
<br>
![](/docs/assets/useful_03_Code_2026-03-27_09.03.24.png)
<br>
<br>
![](/docs/assets/useful_03_Code_2026-03-27_09.03.29.png)
<br>
<br>
![](/docs/assets/useful_03_Code_2026-03-27_09.03.40.png)
<br>
<br>

<!-- [[[end]]] -->

Мне так намного проще бегать по коду

<hr>

## Зачем использовать folding / скрывать блоки кода

1. Проще удерживать важные куски кода в голове

2. Отображать только важное, а неважное - не отображать *(= забрать у всякой чуши в коде возможность нас отвлекать / тратить энергию на распознавание того, что она делает)*

3. Повысить лимит размера файла перед тем, как сочтем, что его пора разбивать на более мелкие, специализированные

4. Сократить количество функций, что вызываются лишь 1 раз *(вместо функции -> inline-им её там, где вызывается -> оборачиваем в fold регион)*

<hr>

## Обычные fold-ы

❌ Не позволяют задать область сокрытия кастомной области кода

❌ Команды «Fold level 1» скрывают все на 1-ом уровне. Но есть более сложные функции, которым я бы хотел описать области сокрытия + задать им summary того, что они делают

<hr>

## Пары `#region` / `#endregion`

❌ Слишком много букв

<hr>

## Big Brain Giga Chad VSCode Расширение [Explicit Folding](https://marketplace.visualstudio.com/items?itemName=zokugun.explicit-folding)

✅ Позволяют задать кастомные области сокрытия кода

✅ Можно прописать им человеческий summary

✅ Можно скрывать все кастомные fold-ы keyboard shortcut-ом *(я по-умолчанию гоняю с скрытыми fold-ами)*

<hr>

## Мои настройки VSCode

```json
// VSCode Preferences: Open User Settings (JSON)
{
  // ...
  "editor.defaultFoldingRangeProvider": "zokugun.explicit-folding",
  "explicitFolding.rules": {
    "*": { "begin": "##", "end": "##" }
  },
  "[python]": {
    "explicitFolding.rules": [
      { "begin": "##", "end": "##" },
      { "begin": "cog}}}", "end": "{{{end}}}" }
    ]
  },
  "[proto]": {
    "explicitFolding.rules": [
      { "begin": "message", "end": "}" },
      { "begin": "cog}}}", "end": "{{{end}}}" }
    ]
  },
  // ...
}
```

PAGE для cog тут заменил [[[]]] на {{{}}}, чтобы у меня кодогенерация не отрабатывал

<hr>

## Настроил с [vscodevim](https://aka.ms/vscodevim)

Биндю

1. Space+0 для сокрытия этих кастомных fold-ов

2. `j` - на `gj,` `k` - на `gk` *(при нажатии вверх/вниз я fold перескакиваю, а не раскрываю его)*

3. `ctrl+d` - на `12j`, `ctrl+u` + на `12k` *(чтобы тоже перескакивали fold-ы)*

4. `l` - `l+editor.unfold`, `0` - `0+editor.unfold`, `^` - `^+editor.unfold`, `$` - `$+editor.unfold`

см [settings.json](https://github.com/hulvdan/.dotfiles/blob/62c0fe4c4886e3bea10903934ddf53913c348f12/vscode/settings.json#L115-L147)

<hr>

## На подумать

- Вкину пару мыслей:

  - Jonathan Blow как-то отмечал что-то вроде: *«Когда ты extract-ишь функцию из другой, ты не упрощаешь код»*

  - Кармак отмечал: *«If a function is only called from a single place, consider inlining it»* ([John Carmack on Inlined Code](http://number-none.com/blow/blog/programming/2014/09/26/carmack-on-inlined-code.html))

- Это я решил затестить подход с разработкой в преимущественно одном файле, о котором говорили Shawn McGrath и Sean Barrett то ли в [On Game Programming #001](https://www.youtube.com/watch?v=lCtALewoFjc), то ли в [#002](https://www.youtube.com/watch?v=s4-wS9VRuvk)

- **Безумие moment.** Ходят легенды, что я в одном файле писал геймплей + рендер клона Brotato. [14к+ строк](https://github.com/hulvdan/cookier/blob/492ed2d9269ccdd93f0c746df97852e737c98e1f/src/game/bf_game.cpp). И довел игру до конца. Хочу этим сказать, что у меня сложилось впечатление, что с помощью удобных fold-ов в голове удерживать более обширную картину кода становится проще

<hr>

## <center>[Hulvdan](/)</center>


