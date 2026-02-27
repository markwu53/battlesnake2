def cond(*pred):
    def fn(f):
        def fc(moves):
            if all(pred):
                return f(moves)
        return fc
    return fn

def avoid_two_step_collision(moves):
    return moves

f = cond(2 > 1)(avoid_two_step_collision)

print(f.__name__)