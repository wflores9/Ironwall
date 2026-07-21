#include "ironwall/lobby.hpp"
#include "ironwall/tee.hpp"
#include <cassert>
#include <iostream>

int main() {
    using namespace ironwall;
    Lobby lobby;
    TeeAttestation tee;
    auto att = tee.generate();

    auto ticket = lobby.issue_ticket("player_42", att);
    assert(!ticket.ticket_id.empty());
    assert(lobby.validate_ticket(ticket));

    // tamper
    auto bad = ticket;
    bad.player_id = "hacker";
    assert(!lobby.validate_ticket(bad));

    auto sid = lobby.open_session(ticket);
    assert(!sid.empty());
    assert(lobby.session_active(sid));
    assert(lobby.active_count() == 1);
    lobby.close_session(sid);
    assert(!lobby.session_active(sid));

    auto hello = lobby.make_hello_frame("player_42", "0.1.0", att);
    assert(hello.size() > 42); // frame + hmac
    auto welcome = lobby.make_welcome_frame(sid);
    assert(welcome.size() > 42);

    std::cout << "lobby_test OK\n";
    return 0;
}
