import os,imageio
import imageio.v2 as imageio
import torch
import numpy as np
import cv2 as cv
from camera_pose_visualizer import CameraPoseVisualizer
'''
Output: images, poses, bds, render_pose, itest;

poses (是指的 c2w 的pose)
'''

def load_kitti360_data(datadir, factor=8):
    poses, imgs, K, i_test =_load_data(datadir)
    H,W = imgs.shape[1:3]
    focal = K[0][0]

    ## 设第一张相机的Pose 是单位矩阵，对其他相机的Pose 需要进行调整为相对于第一帧的Pose 相对位姿
    poses = Normailize_T(poses)   ## 对于 平移translation 进行归一化

    render_pose = np.stack(poses[i] for i in i_test)

    '''     Visual Camera Pose 
    visualizer = CameraPoseVisualizer([-5, 5], [-5, 5], [0, 5])
    for i in np.arange(poses.shape[0]):
        if i % 1 == 0:
            visualizer.extrinsic2pyramid(poses[i])
    visualizer.show()
    '''



    return poses,imgs,render_pose,[H,W,focal],i_test


def _load_data(datadir,end_iterion=424,sequence ='2013_05_28_drive_0000_sync'):
    '''Load intrinstic matrix'''
    intrinstic_file = os.path.join(os.path.join(datadir, 'calibration'), 'perspective.txt')
    with open(intrinstic_file) as f:
        lines = f.readlines()
        for line in lines:
            lineData = line.strip().split()
            if lineData[0] == 'P_rect_00:':
                K_00 = np.array(lineData[1:]).reshape(3,4).astype(np.float64)
            elif lineData[0] == 'P_rect_01:':
                K_01 = np.array(lineData[1:]).reshape(3,4).astype(np.float64)
            elif lineData[0] == 'R_rect_01:':
                R_rect_01 = np.eye(4)
                R_rect_01[:3,:3] = np.array(lineData[1:]).reshape(3,3).astype(np.float64)

    '''Load extrinstic matrix'''
    CamPose_00 = {}
    CamPose_01 = {}
    extrinstic_file = os.path.join(datadir,os.path.join('data_poses',sequence))
    cam2world_file_00 = os.path.join(extrinstic_file,'cam0_to_world.txt')
    pose_file = os.path.join(extrinstic_file,'poses.txt')


    ''' Camera_00  to world coordinate '''
    with open(cam2world_file_00,'r') as f:
        lines = f.readlines()
        for line in lines:
            lineData = list(map(float,line.strip().split()))
            CamPose_00[lineData[0]] = np.array(lineData[1:]).reshape(4,4)

    ''' Camera_01 to world coordiante '''
    CamToPose_01 = loadCameraToPose(os.path.join(os.path.join(datadir, 'calibration'),'calib_cam_to_pose.txt'))
    poses = np.loadtxt(pose_file)
    frames = poses[:, 0]
    poses = np.reshape(poses[:, 1:], [-1, 3, 4])
    for frame, pose in zip(frames, poses):
        pose = np.concatenate((pose, np.array([0., 0., 0., 1.]).reshape(1, 4)))
        pp = np.matmul(pose, CamToPose_01)
        CamPose_01[frame] = np.matmul(pp, np.linalg.inv(R_rect_01))



    ''' Load corrlected images camera 00--> index    camera 01----> index+1'''
    def imread(f):
        if f.endswith('png'):
            #return imageio.imread(f, ignoregamma=True)
            return imageio.imread(f, format="PNG-PIL", ignoregamma=True)
        else:
            #return imageio.imread(f)
            return imageio.imread(f, format="PNG-PIL", ignoregamma=True)
    imgae_dir = os.path.join(datadir,sequence)
    image_00 = os.path.join(imgae_dir,'image_00/data_rect')
    image_01 = os.path.join(imgae_dir,'image_01/data_rect')

    start_index = 3353
    num = 8
    all_images = []
    all_poses = []

    for idx in range(start_index,start_index+num,1):
        ## read image_00
        image = imread(os.path.join(image_00,"{:010d}.png").format(idx))/255.0
        all_images.append(image)
        all_poses.append(CamPose_00[idx])

        ## read image_01
        image = imread(os.path.join(image_01, "{:010d}.png").format(idx))/255.0
        all_images.append(image)
        all_poses.append(CamPose_01[idx])


    #
    # imga_file = [os.path.join(imgae_dir,f"{'%010d'% idx}.png") for idx in imgs_idx ]  ##"010d“ 将 idx前面补成10位
    # # length = len(imga_file)
    # imgs = [imread(f)[...,:3]/255. for f in imga_file]
    # for i,idx in enumerate(imgs_idx):
    #     cv.imwrite(f"train/{'%010d'% idx}.png", imgs[i] * 255)

    imgs = np.stack(all_images,-1)
    imgs = np.moveaxis(imgs, -1, 0)
    c2w = np.stack(all_poses)

    '''Generate test file'''
    i_test = np.array([4,10])

    return c2w,imgs, K_00,i_test

def Normailize_T(poses):
    for i,pose in enumerate(poses):
        if i == 0:
            inv_pose = np.linalg.inv(pose)
            poses[i] = np.eye(4)
        else:
            poses[i] = np.dot(inv_pose,poses[i])

    '''New Normalization '''
    scale = poses[-1,2,3]
    print(f"scale:{scale}\n")
    for i in range(poses.shape[0]):
        poses[i,:3,3] = poses[i,:3,3]/scale
        print(poses[i])
    return poses


def loadCameraToPose(filename):
    # open file
    Tr = {}
    lastrow = np.array([0, 0, 0, 1]).reshape(1, 4)
    with open(filename, 'r') as f:
        lines = f.readlines()
        for line in lines:
            lineData = list(line.strip().split())
            if lineData[0] == 'image_01:':
                data = np.array(lineData[1:]).reshape(3,4).astype(np.float64)
                data = np.concatenate((data,lastrow), axis=0)
                Tr[lineData[0]] = data

    return Tr['image_01:']