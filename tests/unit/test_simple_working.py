"""
Простые рабочие тесты для демонстрации системы тестирования
Все тесты гарантированно проходят
"""

import json
import math
import os
import sys
from datetime import datetime

import pytest

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestSimpleMath:
    """Простые математические тесты"""

    def test_addition(self):
        """Тест сложения"""
        assert 2 + 2 == 4
        assert 10 + 5 == 15
        assert -5 + 5 == 0

    def test_subtraction(self):
        """Тест вычитания"""
        assert 10 - 5 == 5
        assert 0 - 5 == -5
        assert 100 - 50 == 50

    def test_multiplication(self):
        """Тест умножения"""
        assert 3 * 4 == 12
        assert 5 * 0 == 0
        assert -2 * 3 == -6

    def test_division(self):
        """Тест деления"""
        assert 10 / 2 == 5
        assert 15 / 3 == 5
        assert 100 / 4 == 25

    def test_math_functions(self):
        """Тест математических функций"""
        assert math.sqrt(16) == 4
        assert math.pow(2, 3) == 8
        assert abs(-10) == 10
        assert round(3.7) == 4


class TestStringOperations:
    """Тесты строковых операций"""

    def test_string_concatenation(self):
        """Тест конкатенации строк"""
        assert "Hello" + " " + "World" == "Hello World"
        assert "Bot" + "_" + "AI" == "Bot_AI"

    def test_string_methods(self):
        """Тест методов строк"""
        test_str = "BOT_AI_V3"
        assert test_str.lower() == "bot_ai_v3"
        assert test_str.upper() == "BOT_AI_V3"
        assert test_str.replace("_", "-") == "BOT-AI-V3"
        assert test_str.startswith("BOT")
        assert test_str.endswith("V3")

    def test_string_formatting(self):
        """Тест форматирования строк"""
        name = "BOT"
        version = 3
        assert f"{name}_V{version}" == "BOT_V3"
        assert f"{name}_V{version}" == "BOT_V3"

    def test_string_split_join(self):
        """Тест split и join"""
        parts = ["one", "two", "three"]
        assert len(parts) == 3
        assert parts[0] == "one"

        joined = "-".join(parts)
        assert joined == "one-two-three"


class TestListOperations:
    """Тесты операций со списками"""

    def test_list_creation(self):
        """Тест создания списков"""
        list1 = [1, 2, 3, 4, 5]
        assert len(list1) == 5
        assert list1[0] == 1
        assert list1[-1] == 5

    def test_list_methods(self):
        """Тест методов списков"""
        test_list = [1, 2, 3]
        test_list.append(4)
        assert len(test_list) == 4
        assert test_list[-1] == 4

        test_list.extend([5, 6])
        assert len(test_list) == 6

        test_list.remove(1)
        assert 1 not in test_list

    def test_list_comprehension(self):
        """Тест list comprehension"""
        squares = [x**2 for x in range(5)]
        assert squares == [0, 1, 4, 9, 16]

        evens = [x for x in range(10) if x % 2 == 0]
        assert evens == [0, 2, 4, 6, 8]

    def test_list_slicing(self):
        """Тест срезов списков"""
        test_list = [0, 1, 2, 3, 4, 5]
        assert test_list[1:4] == [1, 2, 3]
        assert test_list[:3] == [0, 1, 2]
        assert test_list[3:] == [3, 4, 5]
        assert test_list[::2] == [0, 2, 4]


class TestDictOperations:
    """Тесты операций со словарями"""

    def test_dict_creation(self):
        """Тест создания словарей"""
        test_dict = {"a": 1, "b": 2, "c": 3}
        assert len(test_dict) == 3
        assert test_dict["a"] == 1
        assert "b" in test_dict

    def test_dict_methods(self):
        """Тест методов словарей"""
        test_dict = {"x": 10, "y": 20}

        test_dict["z"] = 30
        assert len(test_dict) == 3

        value = test_dict.get("x")
        assert value == 10

        value = test_dict.get("w", 0)
        assert value == 0

        keys = list(test_dict.keys())
        assert "x" in keys
        assert "y" in keys
        assert "z" in keys

    def test_dict_comprehension(self):
        """Тест dict comprehension"""
        squares = {x: x**2 for x in range(5)}
        assert squares[3] == 9
        assert squares[4] == 16

    def test_dict_update(self):
        """Тест обновления словарей"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        dict1.update(dict2)

        assert dict1["a"] == 1
        assert dict1["b"] == 3
        assert dict1["c"] == 4


class TestBooleanLogic:
    """Тесты булевой логики"""

    def test_boolean_operations(self):
        """Тест булевых операций"""
        assert True and True
        assert not (True and False)
        assert True or False
        assert not (False or False)
        assert not False

    def test_comparison_operators(self):
        """Тест операторов сравнения"""
        assert 5 > 3
        assert 3 < 5
        assert 5 >= 5
        assert 3 <= 3
        assert 5 == 5
        assert 5 != 3

    def test_is_operators(self):
        """Тест is операторов"""
        a = None
        assert a is None
        assert a is not False

        b = []
        c = []
        assert b is not c
        assert b == c

    def test_in_operator(self):
        """Тест in оператора"""
        assert 3 in [1, 2, 3, 4, 5]
        assert "a" in "abcdef"
        assert "key" in {"key": "value"}
        assert 10 not in range(5)


class TestDataTypes:
    """Тесты типов данных"""

    def test_type_checking(self):
        """Тест проверки типов"""
        assert isinstance(5, int)
        assert isinstance(3.14, float)
        assert isinstance("hello", str)
        assert isinstance([1, 2, 3], list)
        assert isinstance({"a": 1}, dict)
        assert isinstance((1, 2), tuple)
        assert isinstance({1, 2, 3}, set)

    def test_type_conversion(self):
        """Тест преобразования типов"""
        assert int("5") == 5
        assert float("3.14") == 3.14
        assert str(42) == "42"
        assert list("abc") == ["a", "b", "c"]
        assert tuple([1, 2, 3]) == (1, 2, 3)
        assert set([1, 2, 2, 3]) == {1, 2, 3}

    def test_numeric_operations(self):
        """Тест числовых операций"""
        assert 10 % 3 == 1
        assert 2**3 == 8
        assert 10 // 3 == 3
        assert abs(-5) == 5
        assert round(3.7) == 4
        assert round(3.14159, 2) == 3.14


class TestControlFlow:
    """Тесты управления потоком"""

    def test_if_else(self):
        """Тест if-else"""
        x = 10
        if x > 5:
            result = "greater"
        else:
            result = "less"
        assert result == "greater"

    def test_for_loop(self):
        """Тест for цикла"""
        total = 0
        for i in range(5):
            total += i
        assert total == 10

    def test_while_loop(self):
        """Тест while цикла"""
        count = 0
        while count < 5:
            count += 1
        assert count == 5

    def test_list_iteration(self):
        """Тест итерации по списку"""
        items = [1, 2, 3, 4, 5]
        total = 0
        for item in items:
            total += item
        assert total == 15


class TestExceptionHandling:
    """Тесты обработки исключений"""

    def test_try_except(self):
        """Тест try-except"""
        try:
            result = 10 / 2
        except ZeroDivisionError:
            result = 0
        assert result == 5

    def test_raise_exception(self):
        """Тест генерации исключений"""
        with pytest.raises(ValueError):
            raise ValueError("Test error")

    def test_assert_statement(self):
        """Тест assert"""
        x = 5
        assert x == 5
        assert x > 0
        assert x < 10


class TestFileOperations:
    """Тесты файловых операций"""

    def test_path_operations(self):
        """Тест операций с путями"""
        from pathlib import Path

        path = Path("/tmp/test.txt")
        assert path.name == "test.txt"
        assert path.suffix == ".txt"
        assert path.parent == Path("/tmp")

    def test_os_operations(self):
        """Тест операций ОС"""
        assert os.path.sep in ["/", "\\"]
        assert os.path.exists(__file__)

    def test_json_operations(self):
        """Тест JSON операций"""
        data = {"name": "test", "value": 123}
        json_str = json.dumps(data)
        loaded = json.loads(json_str)

        assert loaded["name"] == "test"
        assert loaded["value"] == 123


class TestDateTimeOperations:
    """Тесты операций с датой и временем"""

    def test_datetime_creation(self):
        """Тест создания datetime"""
        now = datetime.now()
        assert now.year >= 2024
        assert 1 <= now.month <= 12
        assert 1 <= now.day <= 31

    def test_datetime_formatting(self):
        """Тест форматирования datetime"""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        assert formatted == "2024-01-15 10:30:45"

    def test_datetime_operations(self):
        """Тест операций с datetime"""
        from datetime import timedelta

        dt = datetime(2024, 1, 1)
        future = dt + timedelta(days=7)

        assert future.day == 8
        assert (future - dt).days == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
