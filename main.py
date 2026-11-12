import os
import re
import json
import math
import random
import threading
import urllib.request

from kivy.app import App
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Rectangle, Line

# URL do Webhook do Matusalém Assamita Ur-Shulgi
WEBHOOK_URL = "https://discord.com/api/webhooks/1568818499554512896/zMRDTAPfSXbLzYLBK2EIp4Cv9df3EvY_pXEr6I7UkqflAfzrhSHaLEHbYXn4kKe7zA_1"

ESCALA_DEGRADACAO = {
    0: ("Plenitude e Controle Total", "Sem penalidades"),
    1: ("Murmúrio Distante da Besta", "-0 dados"),
    2: ("Irritabilidade / Foco Predatório", "-1 dado em combate"),
    3: ("Instinto Suplantando a Razão", "-1 dado Social | -2 Disciplina"),
    4: ("Urgência de Sangue / Paranoia", "-3 dados em todos os testes"),
    5: ("Iminência de Frenesi / Vazio", "-5 combate | Rouse Check p/ Frenesi"),
}

COMPULSOES_FOME = {
    0: "Sem compulsão ativa.",
    1: "Foco Predatório (+1 Social vs mortais).",
    2: "Foco Predatório (+1 Social vs mortais).",
    3: "Instinto (-1 Social com mortais).",
    4: "Urgência (Deve alimentar-se nesta cena ou sofre -3 dados na próxima).",
    5: "Vassalagem (-4 dados em ações fora alimentação; Rouse Check Frenesi Dif 4).",
}

CORES_HEX = {
    "normal": "FFFFFF",
    "sucesso": "00FF00",
    "falha": "FF3333",
    "critico": "FFD700",
    "destaque": "00FFFF",
    "bestial": "FF00FF",
}


class FearCityMobileApp(App):
    def build(self):
        self.title = "Welcome to Fear City — Dice Engine"
        Window.clearcolor = (0.02, 0.02, 0.02, 1)
        self.historico_itens = []

        # Layout raiz responsivo (Vertical para Smartphones Android)
        root = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(4))

        # ─── TOPO: ARTE DO ANJO + CONSOLE DE RESULTADOS SOBRE A LÁPIDE ────────
        top_area = RelativeLayout(size_hint=(1, 0.44))

        bg_file = "bg.png" if os.path.exists("bg.png") else ("bg.jpg" if os.path.exists("bg.jpg") else None)
        if bg_file:
            bg_widget = KivyImage(source=bg_file, allow_stretch=True, keep_ratio=False)
            top_area.add_widget(bg_widget)

        # Caixa de resultados posicionada na metade inferior da arte (sobre a tábua)
        console_container = BoxLayout(
            orientation="vertical",
            size_hint=(0.94, 0.62),
            pos_hint={"center_x": 0.5, "y": 0.04},
            padding=dp(6),
        )
        with console_container.canvas.before:
            Color(0.02, 0.02, 0.02, 0.88)
            self.console_rect = Rectangle(pos=console_container.pos, size=console_container.size)
            Color(0.4, 0.0, 0.0, 1)
            self.console_border = Line(rectangle=(0, 0, 1, 1), width=1.2)
        console_container.bind(pos=self._atualizar_canvas_console, size=self._atualizar_canvas_console)

        self.scroll_console = ScrollView(do_scroll_x=False)
        self.console_label = Label(
            text="[color=#00FFFF]Welcome to Fear City — Ur-Shulgi Online[/color]\n",
            markup=True,
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=dp(13),
        )
        self.console_label.bind(
            width=lambda instance, value: setattr(instance, "text_size", (value, None)),
            texture_size=lambda instance, value: setattr(instance, "height", value[1]),
        )
        self.scroll_console.add_widget(self.console_label)
        console_container.add_widget(self.scroll_console)
        top_area.add_widget(console_container)
        root.add_widget(top_area)

        # ─── BASE: PAINEL DE ROLAGEM ROLÁVEL PARA TOQUE ───────────────────────
        painel_scroll = ScrollView(size_hint=(1, 0.56), do_scroll_x=False)
        painel = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6), size_hint_y=None)
        painel.bind(minimum_height=painel.setter("height"))

        # Cabeçalho + Identificação
        painel.add_widget(
            Label(
                text="[b][color=#CC0000]PAINEL DE ROLAGEM (V20 / V5)[/color][/b]",
                markup=True,
                size_hint_y=None,
                height=dp(24),
                font_size=dp(15),
            )
        )

        linha_id = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        linha_id.add_widget(Label(text="Personagem:", size_hint_x=0.35, font_size=dp(13)))
        self.entry_jogador = TextInput(
            text="Narrador",
            multiline=False,
            size_hint_x=0.65,
            background_color=(0.1, 0.1, 0.1, 1),
            foreground_color=(0, 1, 1, 1),
            halign="center",
            font_size=dp(14),
        )
        linha_id.add_widget(self.entry_jogador)
        painel.add_widget(linha_id)

        # 1. Ações Rápidas
        linha_acoes = GridLayout(cols=2, size_hint_y=None, height=dp(38), spacing=dp(6))
        btn_moeda = Button(text="Cara ou Coroa", background_color=(0.18, 0.18, 0.18, 1), bold=True)
        btn_moeda.bind(on_release=lambda *_: self.cmd_cara_coroa())
        btn_rouse = Button(text="Teste do Despertar", background_color=(0.18, 0.18, 0.18, 1), bold=True)
        btn_rouse.bind(on_release=lambda *_: self.cmd_rouse_check())
        linha_acoes.add_widget(btn_moeda)
        linha_acoes.add_widget(btn_rouse)
        painel.add_widget(linha_acoes)

        # 2. Rolagem Híbrida de Dados
        painel.add_widget(
            Label(
                text="[b]Rolagem de Dados (Pool | Tipo | Dif | Loucura):[/b]",
                markup=True,
                size_hint_y=None,
                height=dp(20),
                font_size=dp(12),
            )
        )
        grid_roll = GridLayout(cols=4, size_hint_y=None, height=dp(36), spacing=dp(4))
        self.entry_qtd = TextInput(text="5", multiline=False, input_filter="int", halign="center", background_color=(0.12, 0.12, 0.12, 1), foreground_color=(1, 1, 1, 1))
        self.combo_faces = Spinner(text="d10", values=("d10", "d6", "d4"), background_color=(0.2, 0.2, 0.2, 1))
        self.entry_diff = TextInput(text="6", multiline=False, input_filter="int", halign="center", background_color=(0.12, 0.12, 0.12, 1), foreground_color=(1, 1, 1, 1))
        self.entry_loucura_roll = TextInput(text="0", multiline=False, input_filter="int", halign="center", background_color=(0.25, 0.0, 0.0, 1), foreground_color=(1, 0.84, 0, 1))
        grid_roll.add_widget(self.entry_qtd)
        grid_roll.add_widget(self.combo_faces)
        grid_roll.add_widget(self.entry_diff)
        grid_roll.add_widget(self.entry_loucura_roll)
        painel.add_widget(grid_roll)

        btn_rolar = Button(text="Rolar e Enviar (Discord)", size_hint_y=None, height=dp(38), background_color=(0.35, 0.0, 0.0, 1), bold=True)
        btn_rolar.bind(on_release=lambda *_: self.cmd_rolagem_custom())
        painel.add_widget(btn_rolar)

        # 3. Motor da Besta (Dados da Loucura)
        painel.add_widget(
            Label(
                text="[b][color=#FF4444]MOTOR DA BESTA — DADOS DA LOUCURA[/color][/b]\n[size=11sp](Sangue%/Fome | FV Atual | Humanidade)[/size]",
                markup=True,
                size_hint_y=None,
                height=dp(34),
                halign="center",
            )
        )
        grid_loucura = GridLayout(cols=3, size_hint_y=None, height=dp(36), spacing=dp(4))
        self.entry_sangue_fome = TextInput(text="60%", multiline=False, halign="center", background_color=(0.12, 0.12, 0.12, 1), foreground_color=(1, 1, 1, 1))
        self.entry_fv_atual = TextInput(text="3", multiline=False, input_filter="int", halign="center", background_color=(0.12, 0.12, 0.12, 1), foreground_color=(0, 1, 1, 1))
        self.entry_humanidade = TextInput(text="7", multiline=False, input_filter="int", halign="center", background_color=(0.12, 0.12, 0.12, 1), foreground_color=(1, 1, 1, 1))
        grid_loucura.add_widget(self.entry_sangue_fome)
        grid_loucura.add_widget(self.entry_fv_atual)
        grid_loucura.add_widget(self.entry_humanidade)
        painel.add_widget(grid_loucura)

        grid_checks = GridLayout(cols=3, size_hint_y=None, height=dp(34), spacing=dp(4))
        self.tgl_disc = ToggleButton(text="+1 Disc", font_size=dp(11))
        self.tgl_agrav = ToggleButton(text="+2 Agrav", font_size=dp(11))
        self.tgl_fv_cena = ToggleButton(text="-2 FV Cena", font_size=dp(11))
        grid_checks.add_widget(self.tgl_disc)
        grid_checks.add_widget(self.tgl_agrav)
        grid_checks.add_widget(self.tgl_fv_cena)
        painel.add_widget(grid_checks)

        btn_loucura = Button(
            text="Rolar Dados da Loucura",
            size_hint_y=None,
            height=dp(38),
            background_color=(0.45, 0.0, 0.0, 1),
            color=(1, 0.84, 0, 1),
            bold=True,
        )
        btn_loucura.bind(on_release=lambda *_: self.cmd_sincronizar_e_rolar_loucura())
        painel.add_widget(btn_loucura)

        # 4. Calculadora de Dano
        painel.add_widget(
            Label(
                text="[b]Calculadora de Dano (Tipo | Bruto | Fortitude):[/b]",
                markup=True,
                size_hint_y=None,
                height=dp(20),
                font_size=dp(12),
            )
        )
        grid_dano = GridLayout(cols=3, size_hint_y=None, height=dp(36), spacing=dp(4))
        self.combo_tipo_dano = Spinner(text="Superficial", values=("Superficial", "Agravado"), background_color=(0.2, 0.2, 0.2, 1))
        self.entry_dano_bruto = TextInput(text="0", multiline=False, input_filter="int", halign="center", background_color=(0.12, 0.12, 0.12, 1), foreground_color=(1, 1, 1, 1))
        self.entry_fortitude = TextInput(text="0", multiline=False, input_filter="int", halign="center", background_color=(0.12, 0.12, 0.12, 1), foreground_color=(1, 1, 1, 1))
        grid_dano.add_widget(self.combo_tipo_dano)
        grid_dano.add_widget(self.entry_dano_bruto)
        grid_dano.add_widget(self.entry_fortitude)
        painel.add_widget(grid_dano)

        btn_dano = Button(text="Calcular e Enviar Dano", size_hint_y=None, height=dp(36), background_color=(0.22, 0.22, 0.22, 1), bold=True)
        btn_dano.bind(on_release=lambda *_: self.cmd_calcular_dano())
        painel.add_widget(btn_dano)

        # 5. Histórico Recente + 6. Linha de Comando (!roll)
        painel.add_widget(Label(text="[b]Histórico Local:[/b]", markup=True, size_hint_y=None, height=dp(18), font_size=dp(11)))
        self.lbl_historico = Label(text="Nenhuma rolagem registrada.", size_hint_y=None, height=dp(48), font_size=dp(11), color=(0.65, 0.65, 0.65, 1))
        painel.add_widget(self.lbl_historico)

        linha_cmd = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        self.input_box = TextInput(
            hint_text="Comando (!roll 4d10, !loucura, !ajuda)",
            multiline=False,
            size_hint_x=0.74,
            background_color=(0.06, 0.06, 0.06, 1),
            foreground_color=(1, 1, 1, 1),
        )
        self.input_box.bind(on_text_validate=lambda *_: self.processar_comando_texto())
        btn_cmd = Button(text="Executar", size_hint_x=0.26, background_color=(0.35, 0.0, 0.0, 1), bold=True)
        btn_cmd.bind(on_release=lambda *_: self.processar_comando_texto())
        linha_cmd.add_widget(self.input_box)
        linha_cmd.add_widget(btn_cmd)
        painel.add_widget(linha_cmd)

        painel_scroll.add_widget(painel)
        root.add_widget(painel_scroll)
        return root

    def _atualizar_canvas_console(self, instance, value):
        self.console_rect.pos = instance.pos
        self.console_rect.size = instance.size
        self.console_border.rectangle = (instance.x, instance.y, instance.width, instance.height)

    @mainthread
    def log_console(self, mensagem: str, tag: str = "normal"):
        cor = CORES_HEX.get(tag, "FFFFFF")
        texto_seguro = mensagem.replace("[", "&bl;").replace("]", "&br;")
        self.console_label.text += f"[color=#{cor}]{texto_seguro}[/color]"
        self.scroll_console.scroll_y = 0

    @mainthread
    def log_historico(self, item: str):
        self.historico_itens.insert(0, item)
        self.historico_itens = self.historico_itens[:3]
        self.lbl_historico.text = "\n".join(self.historico_itens)

    def enviar_discord(self, titulo: str, descricao: str, cor_hex: str):
        def tarefa():
            try:
                jogador = self.entry_jogador.text.strip() or "Anônimo"
                cor_int = int(cor_hex.replace("#", ""), 16)
                payload = {
                    "username": "Ur-Shulgi",
                    "avatar_url": "https://i.imgur.com/L1M4rA6.png",
                    "embeds": [{
                        "title": f"🩸 {jogador} | {titulo}",
                        "description": descricao,
                        "color": cor_int,
                    }],
                }
                req = urllib.request.Request(
                    WEBHOOK_URL,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "FearCityAndroid/1.0"},
                )
                urllib.request.urlopen(req, timeout=4)
            except Exception:
                pass

        threading.Thread(target=tarefa, daemon=True).start()

    def mapear_fome_por_entrada(self, valor_str: str):
        s = valor_str.strip().replace("%", "")
        val = int(s)
        if "%" in valor_str or val > 5:
            val = max(0, min(100, val))
            if val >= 90: fome = 0
            elif val >= 70: fome = 1
            elif val >= 50: fome = 2
            elif val >= 30: fome = 3
            elif val >= 10: fome = 4
            else: fome = 5
        else:
            fome = max(0, min(5, val))
        estado, penalidade = ESCALA_DEGRADACAO[fome]
        return fome, estado, penalidade

    def calcular_pool_loucura_painel(self):
        fome_base, estado, penalidade = self.mapear_fome_por_entrada(self.entry_sangue_fome.text)
        fv_atual = max(0, int(self.entry_fv_atual.text or 0))
        hum_atual = max(0, min(10, int(self.entry_humanidade.text or 7)))
        pool = fome_base
        detalhes = [f"Base:{fome_base}"]

        if self.tgl_disc.state == "down":
            pool += 1
            detalhes.append("+1(Disc)")
        if self.tgl_agrav.state == "down":
            pool += 2
            detalhes.append("+2(Agrav)")
        if self.tgl_fv_cena.state == "down":
            pool -= 2
            detalhes.append("-2(FV)")
        if hum_atual > 7:
            red_hum = hum_atual - 7
            pool -= red_hum
            detalhes.append(f"-{red_hum}(Hum)")

        pool_final = max(0, min(10, pool))
        return pool_final, fome_base, fv_atual, estado, penalidade, detalhes

    def cmd_cara_coroa(self):
        resultado = random.choice(["Cara", "Coroa"])
        self.log_console("\n> Alea Jacta Est: ", "normal")
        self.log_console(f"[{resultado}]\n", "destaque")
        self.log_historico(f"Moeda: {resultado}")
        self.enviar_discord("Alea Jacta Est", f"Resultado da moeda: **{resultado}**", "#888888")

    def cmd_rouse_check(self):
        resultado = random.randint(1, 10)
        self.log_console("\n> Teste do Despertar (1d10): ", "normal")
        if resultado >= 6:
            self.log_console(f"[{resultado}] SUCESSO (Fome mantida)\n", "sucesso")
            self.log_historico(f"Despertar: {resultado} (Sucesso)")
            self.enviar_discord("Teste do Despertar", f"Rolagem: **{resultado}**\nResultado: **SUCESSO** (Fome mantida).", "#00FF00")
        else:
            self.log_console(f"[{resultado}] FALHA (+1 Fome / Degradação)\n", "falha")
            self.log_historico(f"Despertar: {resultado} (Falha)")
            self.enviar_discord("Teste do Despertar", f"Rolagem: **{resultado}**\nResultado: **FALHA** (+1 Fome). A Besta tem sede.", "#FF3333")

    def cmd_sincronizar_e_rolar_loucura(self):
        try:
            pool_final, fome_base, fv_atual, estado, penalidade, detalhes = self.calcular_pool_loucura_painel()
            hum_atual = max(0, min(10, int(self.entry_humanidade.text or 7)))
            self.entry_loucura_roll.text = str(pool_final)
        except ValueError:
            self.log_console("\n> Erro: Verifique Sangue/Fome, FV e Humanidade.\n", "falha")
            return

        equacao_str = " ".join(detalhes) + f" = {pool_final}d10"
        self.log_console(f"\n> DADOS DA LOUCURA [{estado}]\n", "bestial")
        self.log_console(f"  Pool: {equacao_str} | FV: {fv_atual}\n  ", "normal")

        if pool_final == 0:
            self.log_console("Plenitude — 0 dados de loucura.\n", "sucesso")
            self.log_historico("Loucura: 0d10 (Plenitude)")
            self.enviar_discord(f"Loucura: {estado}", "Plenitude — A Besta permanece em silêncio (0 dados).", "#00FF00")
            return

        resultados = [random.randint(1, 10) for _ in range(pool_final)]
        crit_limpos, crit_bestiais, falhas_bestiais, sucessos_limpos = 0, 0, 0, 0
        display_discord = []

        for d in resultados:
            if d == 10 and fv_atual > 0 and hum_atual > 0:
                self.log_console(f"[{d}★] ", "destaque")
                display_discord.append(f"**[{d}★]**")
                crit_limpos += 1
                sucessos_limpos += 1
            elif d == 10 and (fv_atual == 0 or hum_atual == 0):
                self.log_console(f"[{d}☠] ", "bestial")
                display_discord.append(f"**[{d}☠]**")
                crit_bestiais += 1
                sucessos_limpos += 1
            elif d == 1:
                self.log_console(f"[{d}⚠] ", "critico")
                display_discord.append(f"**[{d}⚠]**")
                falhas_bestiais += 1
            elif d >= 6:
                self.log_console(f"[{d}] ", "sucesso")
                display_discord.append(f"[{d}]")
                sucessos_limpos += 1
            else:
                self.log_console(f"[{d}] ", "falha")
                display_discord.append(f"{d}")

        self.log_console("\n")
        desc_discord = f"**Dados da Loucura:** {' '.join(display_discord)}\n"
        cor_discord = "#888888"

        if crit_bestiais > 0:
            self.log_console(f"  ☠ CRÍTICO DA BESTA ({crit_bestiais}x): Quebra de Máscara!\n", "bestial")
            desc_discord += f"\n☠ **CRÍTICO DA BESTA ({crit_bestiais}x):** Manifestação violenta da Besta!"
            cor_discord = "#FF00FF"
        if crit_limpos > 0:
            self.log_console(f"  ★ CRÍTICO LIMPO ({crit_limpos}x): FV conteve a Besta!\n", "destaque")
            desc_discord += f"\n★ **CRÍTICO LIMPO ({crit_limpos}x):** FV conteve a Besta."
            if cor_discord == "#888888": cor_discord = "#00FFFF"
        if falhas_bestiais > 0:
            self.log_console(f"  ⚠ FALHA BESTIAL ({falhas_bestiais}x): {COMPULSOES_FOME[fome_base]}\n", "critico")
            desc_discord += f"\n⚠ **FALHA BESTIAL ({falhas_bestiais}x):** {COMPULSOES_FOME[fome_base]}"
            if cor_discord != "#FF00FF": cor_discord = "#FFD700"

        self.log_historico(f"Loucura {pool_final}d10 -> {resultados}")
        self.enviar_discord(f"DADOS DA LOUCURA [{estado}]", desc_discord, cor_discord)

    def cmd_calcular_dano(self):
        try:
            bruto = int(self.entry_dano_bruto.text or 0)
            fort = int(self.entry_fortitude.text or 0)
            tipo = self.combo_tipo_dano.text
            trauma = math.ceil(bruto / 2) if tipo == "Superficial" else bruto
            dano_final = max(0, trauma - fort)

            self.log_console(f"\n> Dano {tipo} [Bruto:{bruto} | Fort:{fort}]: ", "normal")
            self.log_console(f"{dano_final} nível(is)\n", "falha")
            self.log_historico(f"Dano: {dano_final} ({tipo[:3]})")
            self.enviar_discord(
                f"Mitigação de Dano ({tipo})",
                f"**Bruto:** {bruto} | **Fortitude:** {fort}\n🩸 **Dano Final: {dano_final} nível(is)**",
                "#FF3333" if dano_final > 0 else "#888888",
            )
        except ValueError:
            self.log_console("\n> Erro nos valores de dano.\n", "falha")

    def executar_rolagem_hibrida(self, qtd: int, faces: int, diff: int, loucura: int, fv: int):
        if faces != 10: loucura = 0
        loucura = max(0, min(loucura, qtd))
        qtd_normais = qtd - loucura
        res_normais = [random.randint(1, faces) for _ in range(qtd_normais)]
        res_loucura = [random.randint(1, faces) for _ in range(loucura)]

        todos = res_normais + res_loucura
        sucessos_brutos = sum(1 for d in todos if d >= diff)
        falhas_criticas = sum(1 for d in todos if d == 1)
        saldo = max(0, sucessos_brutos - falhas_criticas)

        cab = f"\n> Rolagem {qtd}d{faces} (Dif {diff}" + (f" | L:{loucura} | FV:{fv}" if loucura > 0 else "") + "):\n  "
        self.log_console(cab, "normal")

        disp_normais = []
        for d in res_normais:
            if d == 1:
                self.log_console(f"{d} ", "critico")
                disp_normais.append(f"**{d}**")
            elif d >= diff:
                self.log_console(f"{d} ", "sucesso")
                disp_normais.append(f"**{d}**")
            else:
                self.log_console(f"{d} ", "falha")
                disp_normais.append(f"{d}")

        disp_loucura = []
        for d in res_loucura:
            if d == 10 and fv > 0:
                self.log_console(f"[{d}★] ", "destaque")
                disp_loucura.append(f"**[{d}★]**")
            elif d == 10 and fv == 0:
                self.log_console(f"[{d}☠] ", "bestial")
                disp_loucura.append(f"**[{d}☠]**")
            elif d == 1:
                self.log_console(f"[{d}⚠] ", "critico")
                disp_loucura.append(f"**[{d}⚠]**")
            elif d >= diff:
                self.log_console(f"[{d}] ", "sucesso")
                disp_loucura.append(f"**[{d}]**")
            else:
                self.log_console(f"[{d}] ", "falha")
                disp_loucura.append(f"[{d}]")

        self.log_console(f"\n  Sucessos: {sucessos_brutos} | Falhas(1): -{falhas_criticas} | Saldo: {saldo}\n", "destaque")

        desc_discord = f"**Dados Normais:** {' '.join(disp_normais)}\n"
        if loucura > 0: desc_discord += f"**Dados da Loucura:** {' '.join(disp_loucura)}\n"
        desc_discord += f"\n**Saldo de Sucessos:** {saldo}"
        cor_discord = "#00FF00" if saldo > 0 else "#FF3333"

        if loucura > 0:
            if any(d == 10 for d in res_loucura) and saldo > 0:
                if fv > 0:
                    self.log_console("  ★ CRÍTICO LIMPO (FV protegeu a ação)\n", "destaque")
                    desc_discord += "\n\n★ **CRÍTICO LIMPO:** FV conteve a Besta!"
                    cor_discord = "#00FFFF"
                else:
                    self.log_console("  ☠ CRÍTICO BESTIAL (A Besta assume o controle!)\n", "bestial")
                    desc_discord += "\n\n☠ **CRÍTICO BESTIAL:** A Besta domina a ação!"
                    cor_discord = "#FF00FF"
            if saldo <= 0 and any(d == 1 for d in res_loucura):
                self.log_console("  ⚠ FALHA BESTIAL (Compulsão ou -2 dados!)\n", "critico")
                desc_discord += "\n\n⚠ **FALHA BESTIAL:** Compulsão iminente!"
                cor_discord = "#FFD700"

        self.log_historico(f"{qtd}d{faces} (D:{diff}) -> {saldo} suc")
        self.enviar_discord(f"Rolagem: {qtd}d{faces} (Dif {diff})", desc_discord, cor_discord)

    def cmd_rolagem_custom(self):
        try:
            qtd = int(self.entry_qtd.text or 1)
            faces = int(self.combo_faces.text.replace("d", ""))
            diff = int(self.entry_diff.text or 6)
            loucura = int(self.entry_loucura_roll.text or 0)
            fv = max(0, int(self.entry_fv_atual.text or 1))
            if 1 <= qtd <= 50:
                self.executar_rolagem_hibrida(qtd, faces, diff, loucura, fv)
        except ValueError:
            self.log_console("\n> Erro nos parâmetros numéricos.\n", "falha")

    def processar_comando_texto(self):
        comando = self.input_box.text.strip().lower()
        self.input_box.text = ""
        if not comando:
            return
        if comando in ("!limpar", "!clear"):
            self.console_label.text = ""
            return
        if comando in ("!moeda", "!caracoroa"):
            self.cmd_cara_coroa()
            return
        if comando in ("!despertar", "!rouse"):
            self.cmd_rouse_check()
            return
        if comando in ("!ajuda", "!help"):
            self.log_console("\n> Comandos: !roll Nd10 [dif] [louc] [fv] | !loucura | !dano | !limpar\n", "destaque")
            return
        if comando.startswith("!loucura"):
            self.cmd_sincronizar_e_rolar_loucura()
            return
        if comando.startswith("!roll"):
            match = re.match(r"^!roll\s+(\d+)d(\d+)(?:\s+(\d+))?(?:\s+(\d+))?(?:\s+(\d+))?$", comando)
            if match:
                qtd, faces = int(match.group(1)), int(match.group(2))
                diff = int(match.group(3)) if match.group(3) else None
                loucura = int(match.group(4)) if match.group(4) else 0
                fv = int(match.group(5)) if match.group(5) is not None else int(self.entry_fv_atual.text or 1)
                if diff is None:
                    resultados = [random.randint(1, faces) for _ in range(qtd)]
                    self.log_console(f"\n> {comando}\n  {{ {', '.join(map(str, resultados))} }}\n", "destaque")
                    self.enviar_discord(f"Rolagem: {qtd}d{faces}", f"Resultado: **{resultados}**", "#888888")
                else:
                    self.executar_rolagem_hibrida(qtd, faces, diff, loucura, fv)


if __name__ == "__main__":
    FearCityMobileApp().run()
