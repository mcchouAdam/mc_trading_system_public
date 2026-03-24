cmake_minimum_required(VERSION 3.15)
project(McCoreLib CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(WIN32)
    add_definitions(-DNOMINMAX -DWIN32_LEAN_AND_MEAN -D_WIN32_WINNT=0x0A00)
endif()

find_package(pybind11 CONFIG REQUIRED)

include_directories(include)
include_directories(strategies)

# Define the shared strategy library
add_library(mc_core STATIC
    strategies/YuBrokenBottom.cpp
    strategies/PineL4.cpp
    strategies/MACD.cpp
)

# Force PIC (Position Independent Code) for this static lib
# This is required because it's linked into the shared Python module
set_target_properties(mc_core PROPERTIES POSITION_INDEPENDENT_CODE ON)

# Define the Python module
pybind11_add_module(mc_strategies 
    bindings/py_strategies.cpp
)

target_link_libraries(mc_strategies PRIVATE mc_core)
