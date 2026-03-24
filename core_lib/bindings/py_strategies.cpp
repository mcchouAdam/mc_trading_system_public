#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "Bar.hpp"
#include "BatchUtils.hpp"
#include "MACD.hpp"
#include "PineL4.hpp"
#include "Signal.hpp"
#include "YuBrokenBottom.hpp"

namespace py = pybind11;

PYBIND11_MODULE(mc_strategies, m) {
    py::class_<Bar>(m, "Bar")
        .def(py::init<>())
        .def_readwrite("epic", &Bar::epic)
        .def_readwrite("resolution", &Bar::resolution)
        .def_readwrite("timestamp", &Bar::timestamp)
        .def_readwrite("open", &Bar::open)
        .def_readwrite("high", &Bar::high)
        .def_readwrite("low", &Bar::low)
        .def_readwrite("close", &Bar::close)
        .def_readwrite("volume", &Bar::volume);

    py::enum_<SignalAction>(m, "SignalAction")
        .value("NONE", SignalAction::NONE)
        .value("BUY", SignalAction::BUY)
        .value("SELL", SignalAction::SELL)
        .value("UPDATE_SL", SignalAction::UPDATE_SL)
        .value("CLOSE", SignalAction::CLOSE)
        .export_values();

    py::class_<Signal>(m, "Signal")
        .def_readwrite("epic", &Signal::epic)
        .def_readwrite("action", &Signal::action)
        .def_readwrite("price", &Signal::price)
        .def_readwrite("stop_loss", &Signal::stop_loss)
        .def_readwrite("take_profit", &Signal::take_profit)
        .def_readwrite("strategy_name", &Signal::strategy_name);

    py::class_<BatchResult>(m, "BatchResult")
        .def_readwrite("entries", &BatchResult::entries)
        .def_readwrite("exits", &BatchResult::exits)
        .def_readwrite("short_entries", &BatchResult::short_entries)
        .def_readwrite("short_exits", &BatchResult::short_exits)
        .def_readwrite("exit_prices", &BatchResult::exit_prices)
        .def_readwrite("stop_lines", &BatchResult::stop_lines);

    py::class_<Position>(m, "Position")
        .def(py::init<>())
        .def_readwrite("deal_id", &Position::deal_id)
        .def_readwrite("epic", &Position::epic)
        .def_readwrite("direction", &Position::direction)
        .def_readwrite("entry_price", &Position::entry_price)
        .def_readwrite("current_stop", &Position::current_stop)
        .def_readwrite("current_tp", &Position::current_tp)
        .def_readwrite("highest_high", &Position::highest_high)
        .def_readwrite("lowest_low", &Position::lowest_low)
        .def_readwrite("strategy_name", &Position::strategy_name);

    py::class_<YuBrokenBottom>(m, "YuBrokenBottom")
        .def(py::init<std::map<std::string, double>>())
        .def("on_bar", &YuBrokenBottom::on_bar)
        .def("on_tick", &YuBrokenBottom::on_tick)
        .def("on_position_update", &YuBrokenBottom::on_position_update)
        .def(
            "run_batch",
            [](YuBrokenBottom& self, const std::vector<double>& opens, const std::vector<double>& highs,
               const std::vector<double>& lows, const std::vector<double>& closes, const std::vector<double>& volumes) {
                MarketDataBatch batch{opens, highs, lows, closes, volumes};
                return self.run_batch(batch);
            })
        .def("name", &YuBrokenBottom::name);

    py::class_<PineL4>(m, "PineL4")
        .def(py::init<std::map<std::string, double>>())
        .def("on_bar", &PineL4::on_bar)
        .def("on_tick", &PineL4::on_tick)
        .def("on_position_update", &PineL4::on_position_update)
        .def(
            "run_batch",
            [](PineL4& self, const std::vector<double>& opens, const std::vector<double>& highs,
               const std::vector<double>& lows, const std::vector<double>& closes, const std::vector<double>& volumes) {
                MarketDataBatch batch{opens, highs, lows, closes, volumes};
                return self.run_batch(batch);
            })
        .def("name", &PineL4::name);

    py::class_<MACD>(m, "MACD")
        .def(py::init<std::map<std::string, double>>())
        .def("on_bar", &MACD::on_bar)
        .def("on_tick", &MACD::on_tick)
        .def("on_position_update", &MACD::on_position_update)
        .def(
            "run_batch",
            [](MACD& self, const std::vector<double>& opens, const std::vector<double>& highs,
               const std::vector<double>& lows, const std::vector<double>& closes, const std::vector<double>& volumes) {
                MarketDataBatch batch{opens, highs, lows, closes, volumes};
                return self.run_batch(batch);
            })
        .def("name", &MACD::name);
}
