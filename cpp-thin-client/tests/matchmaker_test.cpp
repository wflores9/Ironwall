#include "ironwall/matchmaker.hpp"
#include "ironwall/tee.hpp"
#include <cassert>
#include <iostream>

int main() {
    using namespace ironwall;
    MatchmakerConfig cfg;
    cfg.players_per_match = 2;
    Matchmaker mm(cfg);
    TeeAttestation tee;

    auto t1 = mm.lobby().issue_ticket("a", tee.generate());
    auto t2 = mm.lobby().issue_ticket("b", tee.generate());
    auto t3 = mm.lobby().issue_ticket("c", tee.generate());

    assert(!mm.enqueue(t1).empty());
    assert(mm.tick().empty()); // need 2
    assert(!mm.enqueue(t2).empty());
    auto m = mm.tick();
    assert(m.size() == 1);
    assert(m[0].players.size() == 2);

    assert(!mm.enqueue(t3).empty());
    assert(mm.queue_size() == 1);

    std::cout << "matchmaker_test OK\n";
    return 0;
}
