cmake_minimum_required(VERSION 3.16)
project(ironwall_cpp VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(IRONWALL_BUILD_TESTS "Build tests" ON)
option(IRONWALL_BUILD_VERIFIER "Build verifier binary" ON)

add_library(ironwall
    src/util.cpp
    src/tee.cpp
    src/zk.cpp
    src/anchors.cpp
    src/challenge.cpp
    src/protocol.cpp
    src/session.cpp
    src/net.cpp
    src/store.cpp
    src/config.cpp
    src/thin_client.cpp
    src/tcp_net.cpp
)

target_include_directories(ironwall
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_compile_options(ironwall PRIVATE -Wall -Wextra -Wpedantic)

add_executable(ironwall_thin_client src/main.cpp)
target_link_libraries(ironwall_thin_client PRIVATE ironwall)

if(IRONWALL_BUILD_VERIFIER)
    add_executable(ironwall_verifier src/verifier.cpp)
    target_link_libraries(ironwall_verifier PRIVATE ironwall)
endif()

if(IRONWALL_BUILD_TESTS)
    enable_testing()
    add_executable(ironwall_tests tests/movement_test.cpp)
    target_link_libraries(ironwall_tests PRIVATE ironwall)
    add_test(NAME movement_tests COMMAND ironwall_tests)
endif()

install(TARGETS ironwall ironwall_thin_client
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)
install(DIRECTORY include/ DESTINATION include)
