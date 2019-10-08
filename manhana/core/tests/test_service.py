from django.test import TestCase
from mixer.backend.django import mixer
import pytest
from manhana.core.services import Arredondamento, CalculaCargahorariaSemanal
from decimal import *


class TestArredondamento(TestCase):

    def test_aula_50_qtd_1(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(0.83), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(1), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(0.83)), valor_valido)
    
    def test_aula_50_qtd_2(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(1.67), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(2), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(1.67)), valor_valido)
    
    def test_aula_50_qtd_3(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(2.50), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(3), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(2.50)), valor_valido)
    
    def test_aula_50_qtd_4(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(3.33), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(4), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(3.33)), valor_valido)
    
    def test_aula_50_qtd_5(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(4.17), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(5), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(4.17)), valor_valido)
    
    def test_aula_50_qtd_6(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(5.00), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(6), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(5.00)), valor_valido)
    
    def test_aula_50_qtd_7(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(5.83), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(7), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(5.83)), valor_valido)
    
    def test_aula_50_qtd_8(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(6.67), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(8), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(6.67)), valor_valido)
    
    def test_aula_50_qtd_9(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(7.50), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(9), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(7.50)), valor_valido)
    
    def test_aula_50_qtd_10(self):
        arredondamento = Arredondamento()
        valor_valido = round(Decimal(8.33), 2)
        self.assertEqual(arredondamento.qtd_horas_aula(10), valor_valido)
        self.assertEqual(arredondamento.arredondar_numero(Decimal(8.33)), valor_valido)


class CalculaCargahorariaSemanalTest(TestCase):

    def test_codigo_horario_qtdaulas_sem_espaco_1_dia_1_aulas(self):
        horario = '2M5'
        ch_semanal = CalculaCargahorariaSemanal()
        retorno = ch_semanal.calcular_qtdaulas(horario)
        self.assertEqual(retorno, 1)

    def test_codigo_horario_qtdaulas_sem_espaco_1_dia_2_aulas(self):
        horario = '2M56'
        ch_semanal = CalculaCargahorariaSemanal()
        retorno = ch_semanal.calcular_qtdaulas(horario)
        self.assertEqual(retorno, 2)

    def test_codigo_horario_qtdaulas_sem_espaco_1_dia_3_aulas(self):
        horario = '4N123'
        ch_semanal = CalculaCargahorariaSemanal()
        retorno = ch_semanal.calcular_qtdaulas(horario)
        self.assertEqual(retorno, 3)

    def test_codigo_horario_qtdaulas_sem_espaco_2_dias_6_aulas_no_mesmo_horario(self):
        horario = '23T123'
        ch_semanal = CalculaCargahorariaSemanal()
        retorno = ch_semanal.calcular_qtdaulas(horario)
        self.assertEqual(retorno, 6)

    def test_codigo_horario_qtdaulas_com_espaco_2_dias_4_aulas_horarios_diferentes(self):
        horario = '2M12 3M56'
        ch_semanal = CalculaCargahorariaSemanal()
        retorno = ch_semanal.calcular_qtdaulas(horario)
        self.assertEqual(retorno, 4)

    def test_codigo_horario_qtdaulas_com_espaco_3_dias_3_aulas_horarios_diferentes(self):
        horario = '2M2 3T2 3T5'
        ch_semanal = CalculaCargahorariaSemanal()
        retorno = ch_semanal.calcular_qtdaulas(horario)
        self.assertEqual(retorno, 3)

    