

import argparse
import os
import sys
import torch
from pathlib import Path
FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative
from datasets.builder_dataset import build_dataset
from models.builder_model import build_model
from utils.optim.builder_optimizer import build_optimizer
from utils.envs.env import init_seeds
from utils.envs.torch_utils import select_device




def parse_opt():
    parser = argparse.ArgumentParser()


    parser.add_argument('--data_type', type=str, default="dance", choices=['dance'],  help='数据格式')
    parser.add_argument('--source', type=str, default=r"E:\work\code\motrv2\data\DanceTrack", help='file/dir/URL/glob, 0 for webcam')
    parser.add_argument('--mode', type=str, default="train", choices=['train', 'test'], help='数据格式')
    parser.add_argument('--batch_size', type=int, default=1, help='total batch size for all GPUs')
    parser.add_argument('--total_epochs', type=int, default=20, help='epoches')


    parser.add_argument('--optim_name', type=str, default="sgd", choices=['sgd'], help='optimizer的选择')
    parser.add_argument('--lr', type=float, default=0.0001, help='lr')
    parser.add_argument('--num_classes', type=int, default=2,  help='类别')

    parser.add_argument('--model_name', type=str, default="diff_track", choices=['resnet', 'diff_track'], help='模型选择')
    parser.add_argument('--weights', nargs='+', type=str, default='False', help='model path(s)')
    parser.add_argument('--resume', default=False, help='model path(s)')

    parser.add_argument('--imgsz', '--img', '--img_size', nargs='+', type=int, default=[(1280, 720)], help='inference size h,w')
    parser.add_argument('--device', default='0', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--project', default=ROOT / 'runs/train', help='save results to project/name')


    # * Matcher
    parser.add_argument('--set_cost_class', default=1, type=float,
                        help="Class coefficient in the matching cost")
    parser.add_argument('--set_cost_bbox', default=5, type=float,
                        help="L1 box coefficient in the matching cost")
    parser.add_argument('--set_cost_giou', default=2, type=float,
                        help="giou box coefficient in the matching cost")

    # * Loss coefficients
    parser.add_argument('--mask_loss_coef', default=1, type=float)
    parser.add_argument('--dice_loss_coef', default=1, type=float)
    parser.add_argument('--bbox_loss_coef', default=5, type=float)
    parser.add_argument('--giou_loss_coef', default=2, type=float)
    parser.add_argument('--eos_coef', default=0.1, type=float,
                        help="Relative classification weight of the no-object class")

    # * Segmentation
    parser.add_argument('--masks', action='store_true',
                        help="Train segmentation head if the flag is provided")
    parser.add_argument('--dec_layers', default=6, type=int,
                        help="Number of decoding layers in the transformer")


    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand

    return opt





from tqdm import tqdm

from utils.losses.builder_loss import build_loss
from datasets.builder_dataset import convert_data2device
from utils.checkpoint.file_utils import get_save_dir


def main(opts):
    init_seeds()
    device = select_device(opts.device, opts.batch_size)  # 设置显卡
    save_dir = get_save_dir(opts.project, opts.resume)
    kwargs_data={'batch_size':opts.batch_size}
    train_dataset, train_loader = build_dataset(opts.data_type, opts.source, mode='train',**kwargs_data)
    dataset_val, val_loader = build_dataset(opts.data_type, opts.source, mode='val',**kwargs_data)
    model = build_model(opts.model_name, opts).to(device)

    model = torch.nn.DataParallel(model)  # DP 模式
    optimizer = build_optimizer(opts.optim_name,model,opts.lr)
    criterion=build_loss('detr_loss',opts)

    for epoch in range(opts.total_epochs):
        model.train()
        with tqdm(total=len(train_loader)) as pbar:
            for pre_imgs, cur_images, pre_targets, cur_targets in train_loader:

                pre_imgs = pre_imgs.to(device)          #data['pre_imgs'].to(device)  #torch.stack(data['pre_imgs'], 0).to(device)   #
                cur_images = cur_images.to(device)      #data['cur_images'].to(device)
                # pre_target = pre_targets.to(device)     #data['pre_targets']
                # cur_target = cur_targets.to(device)     #data['cur_targets']
                pre_targets = convert_data2device(pre_targets,opts.data_type,device)
                cur_targets = convert_data2device(cur_targets, opts.data_type, device)

                # detect_box = [b['boxes'].to(device) for b in pre_targets]

                pred_logits,pred_boxes = model(pre_imgs, cur_images, pre_targets["boxes"])

                outputs={"pred_logits":pred_logits,"pred_boxes":pred_boxes}

                # loss_dict = criterion(outputs, pre_target)

                print(pred_boxes.shape)
                optimizer.zero_grad()

                # loss = criterion(outputs, labels)
                # loss.backward()
                # optimizer.step()
                # np_loss = loss.detach().cpu().numpy()
                # cur_iter = (epoch * len(train_loader)) + iter + 1
                #
                # scheduler.step()
                #
                # #################### 打印信息控制############
                # if (iter+1) % 100 == 0:
                #     print('\tepoch: {}|{}\tloss:{}'.format(epoch + 1, iter + 1, np_loss))
                # pbar.set_description("epoch {}|{}".format(opts.total_epochs, epoch + 1))
                # pbar.set_postfix(iter_all='{}||{}'.format(max_iter, cur_iter),
                #                  iter_epoch='{}||{}'.format(len(train_loader), iter + 1), loss=np_loss)
                # pbar.update()
                #
                # break

            # save_ckpt(os.path.join(save_dir, 'last.pth'), model, optimizer, scheduler, epoch, best_miou)
            # if (epoch) % opts.save_period == 0 and opts.save_period > 0:
            #     pth_name = str(opts.model) + "_" + str(opts.backbone) + '_' + str(epoch+1) + '.pth'
            #     save_ckpt(os.path.join(save_dir, pth_name), model, optimizer, scheduler, epoch, best_miou)
            #
            # if opts.val_period>0 and epoch%opts.val_period!=0:
            #     continue
            #
            #
            # print("\nvalidation...")
            # val_score = validate(model=model, loader=val_loader, device=device, metrics=metrics)
            #
            # if val_score['Mean IoU'] > best_miou:  # save best model
            #     best_miou = val_score['Mean IoU']
            #     save_ckpt(os.path.join(save_dir, 'best.pth'), model, optimizer, scheduler, epoch, best_miou)
            #
            # print('\nOverall Acc\t{}\nFreqW Acc\t{}\nMean IoU\t{}\n'.format(val_score['Overall Acc'],
            #                                                                 val_score['FreqW Acc'],
            #                                                                 val_score['Mean IoU'],
            #                                                                 val_score['Class IoU']))






if __name__ == "__main__":

    opt = parse_opt()
    main(opt)







