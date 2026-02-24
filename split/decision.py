from __future__ import annotations
from . import context
from .models import GameTurn
from .cases import *

# Our magic 'g' shortcut for direct access to data
g: GameTurn = context._helper.g


def decision_flow(moves):
    return seq([
        some_calculations,

        (immediate_kill_opportunity),

        (avoid_single_collision_dead),
        avoid_next_step_no_move,
        avoid_die_in_n_step(2),
        avoid_die_in_n_step(3),
        avoid_suppressed_single_collision,

        (prefer_not(entering_danger(immediate_kill_situation))),

        (prefer_not(entering_danger(trap_kill_situation))),

        avoid_length_change_danger,

        (split_avoid_confinement_2),
        (split_avoid_confinement(factor=1.0)),
        split_avoid_border_trap_2,
        (split_avoid_confinement(factor=1.1)),

        (type_1_collision),

        avoid_two_snake_trap_config_11,
        chasing_kill_opportunity,

        (collision_cut_opportunity),
        (collision_cut_opportunity_2),

        (suppressed_chasing_kill_opportunity),

        avoid_short_vulnerable_move,

        (prefer_not(entering_danger(suppressed_chasing_kill_situation))),
        (prefer_not(entering_danger(border_confront_kill_situation))),

        (make_forming_trap),

        (type_2_collision),

        (trap_kill_opportunity),

        avoid_border_type_1_collision,

        (cond(len(g.others) > 1)(avoid_two_step_collision)),

        avoid_food_split_confine,
        split_avoid_square2,
        (cond(g.me.length >= 9)(split_choice)),

        two_snake_kill_opportunity,

        (cut_kill_opportunity),

        general_suppressed_chasing_kill_opportunity,

        #cond(g.me.length >= 12)(cond([ split_choice, collision_take_risk, ])),
        (attack_vulnerables),
        border_confront_kill_opportunity,
        general_confront_kill_opportunity,

        #(cond(g.me.length >= 12)(split_choice)),
        (cond(len(g.others) == 1)(split_choice)),

        cond(g.me.health < 20)(get_food),

        (wayout),
        wayout_longer_cut,
        (wayout_tail_food),

        (cond(len(g.others) == 1 and g.me.length > g.other.length)(longer_push)),

        #try push not chase my own tail
        cond(len(g.others) == 1 and g.me.length > g.other.length)(longer_push_territory),
        #cond(len(g.others) == 1 and g.me.length > g.other.length)(chase_my_tail),

        (cond(g.me.length > 8)(avoid_next_step_confinement)),

        avoid_single_move(3),

        avoid_two_snake_trap_config_10,
        avoid_two_snake_trap_config_24,
        avoid_two_snake_trap_config_204,
        #(cond(10 <= g.me.length < 12)(split_choice)),
        #cond(7 <= g.me.length <= 9)(collision_take_risk),

        avoid_offborder_trap,
        (type_2_collision_equal_length),
        (cond(g.me.length <= 10)(multi_step_collision)),

        (cond(len(g.others) == 1 and g.me.length >= g.other.length)(avoid_cornered_bordered)),
        cond(g.me.length <= 6)(short_avoid_corner),

        attack_vulnerables_lower_priority,
        cond(len(g.others) > 1)(attempt_border_kill),

        #(cond(7 <= g.me.length < 10)(split_choice)),
        (cond(g.me.length < 10)(split_choice)),

        #cond(len(g.others) == 1 and g.me.length > g.other.length)(push),
        (cond(len(g.others) > 1)(push_2)),
        cond(len(g.others) > 1)(confront_push_4),
        cond(len(g.others) > 1)(corner_push),
        #cond(len(g.others) == 1 and g.me.length > 20)(gain_territory),

        (cond(g.me.length <= 6)(killer_near_prefer_away_border)),

        #try to reproduce this effect earlier when I'm longer than local target
        cond(len(g.others) > 1 and g.me.length >= 10)(local_chasing),

        #cond(g.me.length >= 35)(chase_my_tail),
        avoid_next_step_suppressed,
        avoid_next_step_suppressed_2,

        split_avoid_preliminary_trap,

        next_step_check_food_tail,

        avoid_single_move(2),

        cond(len(g.others) == 1 and g.me.length < g.other.length)(avoid_collision_type_2),

        (get_food),

        enemy_chasing_go_straight,

        (split_choice_2),

        (cond(g.me.length <= 12)(multi_step_collision)),

        (cond(len(g.others) == 1 and g.me.length < g.other.length)(shorter_goto_territory_border)),
        #(cond(len(g.others) > 1)(move_to_largest_territory_component)),

        #switch back to old, the performance wasn't good, not sure if it's caused by the new one
        #choose_a_territory_component,
        move_to_largest_territory_component,
        
        (cond(g.me.length >= 12)(confined_follow_tail)),

        #cond(len(g.others) == 1 and g.me.length > g.other.length)(border_go_up),
        cond(len(g.others) == 1 and g.me.length < g.other.length)(border_go_up),
        #cond(len(g.others) == 1 and g.me.length <= g.other.length)(chase_my_tail_body),

        (cond(g.me.length <= 15)(avoid_single_move(1))),

        avoid_single_move_food,

        avoid_confined_with_killer,

        #sometime this can create type 2 collision situation
        (cond(g.me.length <= 10)(prefer_away_border)),

        (cond(g.me.length >= 10)(prefer_less_split)),

        (split_choice_2),

        avoid_equal_collision,
        (avoid_single_move(1)),

        #prefer_by_score(lambda a: sum(prefer_by_score(a))),
        (prefer(is_straight)),
        #take_random,

        id,
    ])(moves)

def decision():

    #estimated 5-step occupied cells
    g.occupied_cells = [
        occupied_cells(step)
        for step in range(1,11)
    ]
    for snake in g.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in g.occupied_cells[0]]

    if g.turn < 1:
        g.next_coord = take_first(g.me.allowed_moves)
        return

    if len(g.me.allowed_moves) == 0:
        #no allowed moves, die on myself
        g.next_coord = g.me.neck
        return

    if len(g.me.allowed_moves) == 1:
        #no choice
        g.next_coord = g.me.allowed_moves[0]
        return

    if len(g.others) == 0:
        #win
        g.next_coord = g.me.allowed_moves[0]
        return

    #allowed_moves must be 2 or 3
    moves = decision_flow(g.me.allowed_moves)

    g.next_coord = take_first(moves)
