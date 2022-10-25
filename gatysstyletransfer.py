import os
import sys

import matplotlib.pyplot as plt
import torch
from PIL import Image
from torch import nn
from torch import optim
from torch.autograd import Variable
from torch.nn import functional as F
from torchvision import transforms


# constants


# vgg definition that conveniently let's you grab the outputs from any layer
class VGG(nn.Module):
    def __init__(self, pool='max'):
        super(VGG, self).__init__()
        # vgg modules
        self.conv1_1 = nn.Conv2d(3, 64, kernel_size=3, padding=1)
        self.conv1_2 = nn.Conv2d(64, 64, kernel_size=3, padding=1)
        self.conv2_1 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.conv2_2 = nn.Conv2d(128, 128, kernel_size=3, padding=1)
        self.conv3_1 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.conv3_2 = nn.Conv2d(256, 256, kernel_size=3, padding=1)
        self.conv3_3 = nn.Conv2d(256, 256, kernel_size=3, padding=1)
        self.conv3_4 = nn.Conv2d(256, 256, kernel_size=3, padding=1)
        self.conv4_1 = nn.Conv2d(256, 512, kernel_size=3, padding=1)
        self.conv4_2 = nn.Conv2d(512, 512, kernel_size=3, padding=1)
        self.conv4_3 = nn.Conv2d(512, 512, kernel_size=3, padding=1)
        self.conv4_4 = nn.Conv2d(512, 512, kernel_size=3, padding=1)
        self.conv5_1 = nn.Conv2d(512, 512, kernel_size=3, padding=1)
        self.conv5_2 = nn.Conv2d(512, 512, kernel_size=3, padding=1)
        self.conv5_3 = nn.Conv2d(512, 512, kernel_size=3, padding=1)
        self.conv5_4 = nn.Conv2d(512, 512, kernel_size=3, padding=1)
        if pool == 'max':
            self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
            self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
            self.pool3 = nn.MaxPool2d(kernel_size=2, stride=2)
            self.pool4 = nn.MaxPool2d(kernel_size=2, stride=2)
            self.pool5 = nn.MaxPool2d(kernel_size=2, stride=2)
        elif pool == 'avg':
            self.pool1 = nn.AvgPool2d(kernel_size=2, stride=2)
            self.pool2 = nn.AvgPool2d(kernel_size=2, stride=2)
            self.pool3 = nn.AvgPool2d(kernel_size=2, stride=2)
            self.pool4 = nn.AvgPool2d(kernel_size=2, stride=2)
            self.pool5 = nn.AvgPool2d(kernel_size=2, stride=2)

    def forward(self, x, out_keys):
        out = {}
        out['r11'] = F.relu(self.conv1_1(x))
        out['r12'] = F.relu(self.conv1_2(out['r11']))
        out['p1'] = self.pool1(out['r12'])
        out['r21'] = F.relu(self.conv2_1(out['p1']))
        out['r22'] = F.relu(self.conv2_2(out['r21']))
        out['p2'] = self.pool2(out['r22'])
        out['r31'] = F.relu(self.conv3_1(out['p2']))
        out['r32'] = F.relu(self.conv3_2(out['r31']))
        out['r33'] = F.relu(self.conv3_3(out['r32']))
        out['r34'] = F.relu(self.conv3_4(out['r33']))
        out['p3'] = self.pool3(out['r34'])
        out['r41'] = F.relu(self.conv4_1(out['p3']))
        out['r42'] = F.relu(self.conv4_2(out['r41']))
        out['r43'] = F.relu(self.conv4_3(out['r42']))
        out['r44'] = F.relu(self.conv4_4(out['r43']))
        out['p4'] = self.pool4(out['r44'])
        out['r51'] = F.relu(self.conv5_1(out['p4']))
        out['r52'] = F.relu(self.conv5_2(out['r51']))
        out['r53'] = F.relu(self.conv5_3(out['r52']))
        out['r54'] = F.relu(self.conv5_4(out['r53']))
        out['p5'] = self.pool5(out['r54'])
        return [out[key] for key in out_keys]


# gram matrix and loss
class GramMatrix(nn.Module):
    def forward(self, input):
        b, c, h, w = input.size()
        F = input.view(b, c, h * w)
        G = torch.bmm(F, F.transpose(1, 2))
        G.div_(h * w)
        return G


class GramMSELoss(nn.Module):
    def forward(self, input, target):
        out = nn.MSELoss()(GramMatrix()(input), target)
        return (out)


def process_images():
    global prep, postpa, postpb
    # pre and post processing for images
    image_size = 512
    prep = transforms.Compose([transforms.Scale(image_size),
                               transforms.ToTensor(),
                               transforms.Lambda(lambda x: x[torch.LongTensor([2, 1, 0])]),  # turn to BGR
                               transforms.Normalize(mean=[0.40760392, 0.45795686, 0.48501961],  # subtract imagenet mean
                                                    std=[1, 1, 1]),
                               transforms.Lambda(lambda x: x.mul_(255)),
                               ])
    postpa = transforms.Compose([transforms.Lambda(lambda x: x.mul_(1. / 255)),
                                 transforms.Normalize(mean=[-0.40760392, -0.45795686, -0.48501961],  # add imagenet mean
                                                      std=[1, 1, 1]),
                                 transforms.Lambda(lambda x: x[torch.LongTensor([2, 1, 0])]),  # turn to RGB
                                 ])
    postpb = transforms.Compose([transforms.ToPILImage()])


def postp(tensor):  # to clip results in the range [0,1]
    t = postpa(tensor)
    t[t > 1] = 1
    t[t < 0] = 0
    img = postpb(t)
    return img


"""Loading weights to the above self defined VGG architecture"""


def load_weights():
    vgg = VGG()
    vgg.load_state_dict(torch.load('vgg_conv.pth'))
    for param in vgg.parameters():
        param.requires_grad = False
    if torch.cuda.is_available():
        vgg.cuda()
    return vgg


"""load images, ordered as [style_image, content_image]"""


def load_images(style_image_name, content_image_name):
    image_names = ['MLK.jpg', 'sreac.jpg', 'towerhall.jpg', 'cityhall.jpg', 'Crystal.jpeg', 'Evening.jpeg',
                   'Buildings.jpg', 'Trees.jpeg', 'Aditya.jpg', 'Pradeep.jpg']
    # content_image_name = image_names[0]
    img_dirs = [image_path, image_path]
    img_names = [style_image_name, content_image_name]
    imgs = [Image.open(img_dirs[i] + name) for i, name in enumerate(img_names)]
    imgs_torch = [prep(img) for img in imgs]
    if torch.cuda.is_available():
        imgs_torch = [Variable(img.unsqueeze(0).cuda()) for img in imgs_torch]
    else:
        imgs_torch = [Variable(img.unsqueeze(0)) for img in imgs_torch]
    style_image, content_image = imgs_torch
    opt_img = Variable(content_image.data.clone(), requires_grad=True)
    # display images
    i = 0
    fig, axes = plt.subplots(1, 2, figsize=(15, 15))
    for img in imgs:
        axes[i].imshow(img)
        if i == 0:
            axes[i].set_title('Disney Logo')
        else:
            axes[i].set_title('MLK Building')
        i = i + 1
    return opt_img, style_image, content_image


def train(style_layers, content_layers, style_weights, content_weights, vgg, style_image, content_image):
    loss_layers = style_layers + content_layers
    loss_fns = [GramMSELoss()] * len(style_layers) + [nn.MSELoss()] * len(content_layers)
    if torch.cuda.is_available():
        loss_fns = [loss_fn.cuda() for loss_fn in loss_fns]

    weights = style_weights + content_weights

    # compute optimization targets
    style_targets = [GramMatrix()(A).detach() for A in vgg(style_image, style_layers)]
    content_targets = [A.detach() for A in vgg(content_image, content_layers)]
    targets = style_targets + content_targets

    # run style transfer
    max_iter = 500
    show_iter = 50
    optimizer = optim.LBFGS([opt_img])
    n_iter = [0]

    while n_iter[0] <= max_iter:

        def closure():
            optimizer.zero_grad()
            out = vgg(opt_img, loss_layers)
            layer_losses = [weights[a] * loss_fns[a](A, targets[a]) for a, A in enumerate(out)]
            loss = sum(layer_losses)
            loss.backward()
            n_iter[0] += 1
            print(n_iter[0])
            # print loss
            if n_iter[0] % show_iter == (show_iter - 1):
                print('Iteration: %d, loss: %f' % (n_iter[0] + 1, loss.item()))
            # print([loss_layers[li] + ': ' +  str(l.data[0]) for li,l in enumerate(layer_losses)]) #loss of each layer
            return loss

        optimizer.step(closure)


""" Now, we do experimentation by choosing different layers for Style and Content.\
First, we choose 'r11' and 'r21' for style and 'r42' for content.
"""


def conduct_first_experiment(opt_img, vgg, style_image, content_image):
    style_layers = ['r11', 'r21']
    content_layers = ['r42']
    style_weights = [1e3 / n ** 2 for n in [64, 128]]
    content_weights = [1e0]
    train(style_layers, content_layers, style_weights, content_weights, vgg, style_image, content_image)
    # display result
    print("Displaying results of first experiment")
    out_img1 = postp(opt_img.data[0].cpu().squeeze())
    plt.imshow(out_img1)
    plt.gcf().set_size_inches(10, 10)
    plt.show()
    return out_img1


def plot_images(axs, i, j, imgs, imgs_spongebob, imgs_monalisa, imgs_studio_ghibli, imgs_disney):
    axs[i, 0].imshow(imgs[j].resize(imgs_monalisa[j].size))
    axs[i, 1].imshow(imgs_monalisa[j])
    axs[i, 2].imshow(imgs_disney[j])
    axs[i, 3].imshow(imgs_studio_ghibli[j])
    axs[i, 4].imshow(imgs_spongebob[j])
    axs[i, 0].set_title('Input image')
    axs[i, 1].set_title('Monalisa')
    axs[i, 2].set_title('Disney')
    axs[i, 3].set_title('Studio Ghibli')
    axs[i, 4].set_title('Spongebob Squarepants')


"""Plotting the results"""


def plot_results():
    image_names = ['MLK.jpg', 'sreac.jpg', 'towerhall.jpg', 'cityhall.jpg', 'Crystal.jpeg', 'Evening.jpeg',
                   'Buildings.jpg',
                   'Trees.jpeg', 'Aditya.jpg', 'Pradeep.jpg']
    image_dir = "Output_Images/"
    imgs = [Image.open('Images/' + name) for i, name in enumerate(image_names)]
    imgs_spongebob = [Image.open(image_dir + "spongebob_" + name) for i, name in enumerate(image_names)]
    imgs_monalisa = [Image.open(image_dir + 'monalisa_' + name) for i, name in enumerate(image_names)]
    imgs_studio_ghibli = [Image.open(image_dir + 'studio_ghibli_' + name) for i, name in enumerate(image_names)]
    imgs_disney = [Image.open(image_dir + 'disney_' + name) for i, name in enumerate(image_names)]
    fig, axs = plt.subplots(4, 5, figsize=(18, 11), sharex=True, sharey=True)
    for i in range(4):
        j = i
        plot_images(axs, i, j, imgs, imgs_spongebob, imgs_monalisa, imgs_studio_ghibli, imgs_disney)
    fig, axs = plt.subplots(4, 5, figsize=(18, 11), sharex=True, sharey=True)
    for i in range(4):
        j = i + 4
        plot_images(axs, i, j, imgs, imgs_spongebob, imgs_monalisa, imgs_studio_ghibli, imgs_disney)
    fig, axs = plt.subplots(2, 5, figsize=(15, 6), sharex=True, sharey=True)
    for i in range(2):
        j = i + 8
        plot_images(axs, i, j, imgs, imgs_spongebob, imgs_monalisa, imgs_studio_ghibli, imgs_disney)
    plt.show()
    return imgs


""" Now we run the second experiment. We use 3 layers r11, r21, r31 for extracting the style 
 and r42 and r32  for extracting the content."""


def conduct_second_experiment(opt_img, vgg, style_image, content_image):
    style_layers = ['r11', 'r21', 'r31']
    content_layers = ['r42', 'r32']
    style_weights = [1e3 / n ** 2 for n in [64, 128, 256]]
    content_weights = [1e0, 1e0]
    train(style_layers, content_layers, style_weights, content_weights, vgg, style_image, content_image)
    # display result
    print("Displaying results of second experiment")
    out_img2 = postp(opt_img.data[0].cpu().squeeze())
    plt.imshow(out_img2)
    plt.gcf().set_size_inches(10, 10)
    plt.show()
    return out_img2


""" Now we run the third experiment. Let's now use 5 layers r11, r21, r31, r41 and r51 for extracting the style 
and r42, r32 and r22 for extracting the content."""


def conduct_third_experiment(opt_img, vgg, style_image, content_image):
    global style_layers, content_layers, style_weights, content_weights, out_img3
    style_layers = ['r11', 'r21', 'r31', 'r41', 'r51']
    content_layers = ['r42', 'r32', 'r22']
    style_weights = [1e3 / n ** 2 for n in [64, 128, 256, 512, 512]]
    content_weights = [1e0, 1e0, 1e0]
    train(style_layers, content_layers, style_weights, content_weights, vgg, style_image, content_image)
    print("Displaying results of third experiment")
    out_img3 = postp(opt_img.data[0].cpu().squeeze())
    plt.imshow(out_img3)
    plt.gcf().set_size_inches(10, 10)
    plt.show()
    return out_img3


"""Lets compare the 3 results we obtained"""


def compare_results(imgs, out_img1, out_img2, out_img3):
    print("comparing the three outputs")
    fig, ax = plt.subplots(2, 2, figsize=(15, 10))
    ax[0, 0].imshow(imgs)
    ax[0, 0].title.set_text('Image')
    ax[0, 1].imshow(out_img1)
    ax[0, 1].title.set_text('First Output')
    ax[1, 0].imshow(out_img2)
    ax[1, 0].title.set_text('Second Output')
    ax[1, 1].imshow(out_img3)
    ax[1, 1].title.set_text('Third Output')
    plt.show()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Incorrect number of arguments")
        exit(0)

    image_path = 'Images/'
    style_image_name = sys.argv[1]
    content_image_name = sys.argv[2]

    if (not os.path.exists(image_path + style_image_name) or not os.path.exists(image_path + content_image_name)):
        print("File does not exist")
        exit(1)

    # content_image_name = "MLK.jpg"
    # style_image_name = "disney.jpg"

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(device)
    process_images()
    vgg = load_weights()
    opt_img, style_image, content_image = load_images(style_image_name, content_image_name)

    print("conducting the first experiment")
    out_img1 = conduct_first_experiment(opt_img, vgg, style_image, content_image)
    # saving the result
    print("saving the file")
    out_image1_name = 'Output_Images/' + style_image_name.split('.')[0] + "_" + content_image_name.split('.')[
        0] + "_1.jpeg"
    out_img1.save(out_image1_name)
    print("file saved")
    print("Plotting results")
    imgs = plot_results()
    print("conducting the second experiment")
    out_img2 = conduct_second_experiment(opt_img, vgg, style_image, content_image)
    out_image2_name = 'Output_Images/' + style_image_name.split('.')[0] + "_" + content_image_name.split('.')[
        0] + "_2.jpeg"
    out_img2.save(out_image2_name)
    print("conducting the third experiment")
    out_img3 = conduct_third_experiment(opt_img, vgg, style_image, content_image)
    out_image3_name = 'Output_Images/' + style_image_name.split('.')[0] + "_" + content_image_name.split('.')[
        0] + "_3.jpeg"
    out_img3.save(out_image3_name)
    compare_results(Image.open('Images/' + content_image_name), Image.open(out_image1_name),
                    Image.open(out_image2_name), Image.open(out_image3_name))
