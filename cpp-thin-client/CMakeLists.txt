cmake_minimum_required(VERSION 3.16)
project(ironwall_cpp VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(IRONWALL_BUILD_TESTS "Build tests" ON)
option(IRONWALL_BUILD_VERIFIER "Build verifier binary" ON)
option(IRONWALL_BUILD_SHARED "Build shared lib for P/Invoke" ON)

set(IRONWALL_SOURCES
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
    src/c_api.cpp
    src/chain_submit.cpp
)

add_library(ironwall_static STATIC ${IRONWALL_SOURCES})
target_include_directories(ironwall_static
    PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
           $<INSTALL_INTERFACE:include>
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
)
target_compile_options(ironwall_static PRIVATE -Wall -Wextra -Wpedantic)
set_target_properties(ironwall_static PROPERTIES OUTPUT_NAME ironwall)

if(IRONWALL_BUILD_SHARED)
    add_library(ironwall_shared SHARED ${IRONWALL_SOURCES})
    target_include_directories(ironwall_shared
        PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
               $<INSTALL_INTERFACE:include>
        PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
    )
    target_compile_options(ironwall_shared PRIVATE -Wall -Wextra -Wpedantic)
    set_target_properties(ironwall_shared PROPERTIES OUTPUT_NAME ironwall)
endif()

add_executable(ironwall_thin_client src/main.cpp)
target_link_libraries(ironwall_thin_client PRIVATE ironwall_static)

if(IRONWALL_BUILD_VERIFIER)
    add_executable(ironwall_verifier src/verifier.cpp)
    target_link_libraries(ironwall_verifier PRIVATE ironwall_static)
endif()

if(IRONWALL_BUILD_TESTS)
    enable_testing()
    add_executable(ironwall_tests tests/movement_test.cpp)
    target_link_libraries(ironwall_tests PRIVATE ironwall_static)
    add_test(NAME movement_tests COMMAND ironwall_tests)
endif()

install(TARGETS ironwall_static
    LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin)
if(IRONWALL_BUILD_SHARED)
    install(TARGETS ironwall_shared
        LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin)
endif()
install(DIRECTORY include/ DESTINATION include)

add_executable(ironwall_chain_smoke src/chain_smoke.cpp)
target_link_libraries(ironwall_chain_smoke PRIVATE ironwall_static)
