"""Run:  cd backend && python -m unittest discover -s tests -v   (or: pytest)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rules import all_params, check  # noqa: E402

KHATA = {"entries": [
    {"date": "2026-07-03", "name": "Karim", "amount": 1200, "kind": "credit"},
    {"date": "2026-07-19", "name": "Nasima", "amount": 3100, "kind": "credit"},
    {"date": "2026-08-12", "name": "Karim", "amount": 1500, "kind": "credit"},
    {"date": "2026-08-15", "name": "Rahima", "amount": 850, "kind": "credit"},
    {"date": "2026-08-20", "name": "Salam", "amount": 2300, "kind": "credit"},
    {"date": "2026-09-02", "name": "Salam", "amount": 500, "kind": "payment"},
    {"date": "2026-09-10", "name": "Jamal", "amount": 640, "kind": "credit"},
    {"date": "2026-09-20", "name": "Karim", "amount": 1500, "kind": "credit"},
]}


class Payslip(unittest.TestCase):
    def test_underpaid_sample(self):
        r = check("payslip", {"basic": 8000, "otHours": 60, "otPaid": 3000})
        self.assertAlmostEqual(r["shouldPay"], 4615.38, places=2)
        self.assertAlmostEqual(r["difference"], 1615.38, places=2)
        self.assertTrue(r["flagged"])

    def test_correct_pay_not_flagged(self):
        r = check("payslip", {"basic": 8000, "otHours": 60, "otPaid": 4615.38})
        self.assertFalse(r["flagged"])
        self.assertEqual(r["difference"], 0)

    def test_missing_value(self):
        with self.assertRaises(ValueError):
            check("payslip", {"basic": 8000, "otHours": 60})

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            check("payslip", {"basic": -1, "otHours": 60, "otPaid": 0})


class Loan(unittest.TestCase):
    def test_flat_15_is_much_higher_in_reality(self):
        r = check("loan", {"principal": 30000, "flat": 15, "months": 12, "inst": 2875})
        self.assertAlmostEqual(r["realYearlyRatePct"], 26.6, delta=0.2)
        self.assertEqual(r["totalRepay"], 34500)
        self.assertEqual(r["extraPaid"], 4500)
        self.assertTrue(r["aboveGuideline"])
        self.assertTrue(r["installmentMatchesPrinted"])

    def test_zero_interest(self):
        r = check("loan", {"principal": 12000, "flat": 0, "months": 12, "inst": 1000})
        self.assertEqual(r["realYearlyRatePct"], 0)
        self.assertFalse(r["aboveGuideline"])

    def test_installment_mismatch_detected(self):
        r = check("loan", {"principal": 30000, "flat": 15, "months": 12, "inst": 3200})
        self.assertFalse(r["installmentMatchesPrinted"])


class Bill(unittest.TestCase):
    def test_slabs_and_overcharge(self):
        r = check("bill", {"units": 320, "demand": 84, "misc": 450, "total": 2862.8})
        self.assertAlmostEqual(r["energy"], 2213.9, places=2)
        self.assertAlmostEqual(r["shouldTotal"], 2412.80, delta=0.01)
        self.assertAlmostEqual(r["difference"], 450.0, delta=0.1)
        self.assertTrue(r["flagged"])
        self.assertEqual([s["units"] for s in r["slabs"]], [75, 125, 100, 20])

    def test_correct_bill_not_flagged(self):
        r = check("bill", {"units": 320, "demand": 84, "misc": 0, "total": 2412.80})
        self.assertFalse(r["flagged"])

    def test_units_above_last_fixed_slab(self):
        r = check("bill", {"units": 700, "demand": 0, "total": 0})
        self.assertEqual(r["slabs"][-1]["rate"], 14.61)
        self.assertEqual(r["slabs"][-1]["units"], 100)


class Khata(unittest.TestCase):
    def test_balances_and_overdue(self):
        r = check("khata", KHATA, as_of="2026-09-30")
        self.assertEqual(r["totalOutstanding"], 10590)
        self.assertEqual(r["customers"][0]["name"], "Karim")
        self.assertEqual(r["customers"][0]["balance"], 4200)
        self.assertEqual(r["customers"][0]["ageDays"], 89)
        self.assertEqual(r["overdueAmount"], 4300)  # Only aged unpaid lots: Karim 1200 + Nasima 3100

    def test_payment_reduces_balance(self):
        r = check("khata", KHATA, as_of="2026-09-30")
        salam = next(c for c in r["customers"] if c["name"] == "Salam")
        self.assertEqual(salam["balance"], 1800)

    def test_fully_paid_customer_disappears(self):
        e = [{"date": "2026-09-01", "name": "A", "amount": 100, "kind": "credit"},
             {"date": "2026-09-05", "name": "A", "amount": 100, "kind": "payment"}]
        self.assertEqual(check("khata", {"entries": e}, as_of="2026-09-30")["customers"], [])

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            check("khata", {"entries": []})


class Config(unittest.TestCase):
    def test_all_params_exposed(self):
        p = all_params()
        self.assertEqual(p["payslip"]["monthly_divisor"], 208)
        self.assertEqual(p["loan"]["guideline_cap_percent"], 24)
        self.assertIsNone(p["bill"]["slabs"][-1]["units"])


if __name__ == "__main__":
    unittest.main()
