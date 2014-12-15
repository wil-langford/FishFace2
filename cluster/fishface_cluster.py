from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

print "I am rank {}.".format(rank)

if rank == 0:
    # I get to be in charge!  I'm so excited!

    for i in range(size):
        data = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG)
        print "I see drone {}.".format(data['rank'])

else:
    # I'm a drone.
    print "I'm rank {} and I'm telling the boss about myself.".format(rank)
    comm.send({'rank': rank}, dest=0, tag=rank)
