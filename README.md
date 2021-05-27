# 介绍
ChiaTools是Chia官方钱包P图功能的替代品，提供了比官方钱包更简单更方便更实用的P图功能。同时集成了hpool矿池挖矿功能。

ChiaTools是免费的开源软件，同时欢迎各位开发者朋友们一起贡献代码，加入QQ群 926625265 来一起交流和完善ChiaTools。

近期发现有人在利用该软件进行着非法牟利。再次提醒，该软件为免费软件，所有类似的收费软件都为非法。

## 下载地址
https://gitee.com/devteamcn/chia-tools/releases

下载解压后，进入目录找到ChiaTools.exe，双击启动。

# 功能亮点
- 可以高效率的并发P图任务
- P图任务可以自动选择最终目录，无需担心磁盘会满导致任务失败
- P图进度精细到1%
- P图过程可随时暂停和继续，自定义暂停时间
- 任务可以延迟启动，任务之间可以错开高峰，只需一次配置即可全自动P图
- 集成了HPool挖矿程序，当挖矿程序异常或崩溃时会自动重启程序
- 不索要助记词，当安装了Chia钱包软件并创建了钱包，会自动获取公钥
- 失败的任务在删除任务时自动删除临时文件
- 当P图最后一步拷贝文件前，自动开始下一个任务，无需担心机械硬盘阻塞影响P图速度
- P图执行过程中可随时修改配置，配置完后下个任务生效
- P图命令行可自由选择，选择内置P图程序，或官方钱包命令行
## 软件界面
### 硬盘
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/folder01.jpg)
### P图任务
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/plot01.jpg)
### 创建P图任务
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/create01.jpg)
### 矿池挖矿
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/mine01.jpg)

# 使用说明
## 配置硬盘
首先要配置硬盘，在硬盘界面里，将所有的固态硬盘和机械硬盘分别添加到对应的列表中。
## 创建P图任务
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/create02.jpg)

### P图程序
P图命令行分为两种，一种是官方钱包chia.exe，一种是内置的ProofOfSpace.exe
#### 官方钱包chia.exe
官方钱包chia.exe是只有安装了Chia钱包软件才会有，所在位置是
C:\Users\Administrator\AppData\Local\chia-blockchain\app-1.1.4\resources\app.asar.unpacked\daemon\chia.exe
#### ProofOfSpace.exe
ProofOfSpace.exe是chia官方提供的开源代码编译出来的P图程序，和钱包chia.exe本质上是使用的相同代码，但是命令行参数不同。当在没有安装钱包软件的电脑上可以使用该程序。

这两个程序P图速度在理论上没有区别，如果你有发现了区别，请联系我们一起交流。
### 临时目录
可选择在硬盘界面中配置的固态硬盘
### 最终目录
默认选择自动。在选择自动时，软件会在开始任务前自动选择空闲的硬盘，当没有可用的空闲硬盘时，任务会停止。

也可以指定最终目录，当指定的硬盘空间不够时，任务会停止
### fpk和ppk
如果你安装了Chia钱包软件并且创建了钱包，软件会自动获取fpk和ppk。如果没有安装钱包，请使用第三方工具（如：HPool提供的签名软件等）来生成。
### Plot大小
默认选择k32，注意每种所需的临时文件大小是不同的。
### 最大内存
默认内存是4608MiB，可自定义大小。注意要合理分配内存，记得预留内存给操作系统，以免造成P图失败。
### 线程数
默认线程数是2，可根据CPU线程数自由配置。
### 桶数
默认桶数是128，范围是16-128。
### 开启位域
默认是开启。位域是利用了CPU的一种特性，可大大提高P图效率。如果你的CPU不支持这种特性，需要禁止位域。
### 指定数量
如果不指定数量，会不停的P图直到硬盘满。

如果指定了数量，会只P指定的数量的图。注意这些任务数量是按顺序执行，不是并发执行。如果要并发执行，需要创建多条任务。
### 延迟时间
如果不设置延迟时间，任务会立即开始。如果指定了延迟时间，会等待这个时间后自动开始。

如果你想让同一个固态硬盘下的多个任务错开高峰，可以自定义延迟时间来运行任务。
## P图任务管理
右键一个正在执行的P图任务，会弹出下面菜单。
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/menu01.jpg)
### 查看日志
查看日志可以查看任务输出的实时日志内容。
### 编辑
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/edit01.jpg)
编辑任务可以在任务运行过程中修改配置，修改之后会在下个任务执行时生效。
### 停止
会强制停止正在运行的任务，注意停止后无法恢复。
### 暂停 / 继续
在P图任务执行过程中可随时暂停任务，暂停的过程中会停止硬盘的读写，CPU占用为0。点击继续会恢复运行。

可以指定暂停时间30分钟、1小时、2小时、3小时、4小时。到时间后会自动继续任务。
### 浏览临时文件
点击后会跳转到该任务的临时文件所在的目录。
## P图任务辅助功能
在P图任务界面的下方，会有任务数量的限制。
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/plot02.jpg)
### 限制阶段1的任务数量
当创建了多个P图任务，此时只会有指定数量的任务处于阶段1执行，其它任务会处于排队中的状态。
### 限制总任务数量
当创建了多个P图任务，此时只会有指定数量的任务执行，其它任务会处于排队中的状态。
### 完成后自动重新挖矿
勾选之后，当一个P图任务完成，会生成新的Plot文件。此时如果你正在挖矿，会自动重新启动挖矿程序，重启后的挖矿程序会立即扫描所有plot文件。如果没有挖矿，
则不会有任何效果。

如果不勾选，正在运行的挖矿程序会每间隔10分钟扫盘一次。
## 使用HPool矿池挖矿
目前只支持HPool挖矿，后续如果有别的的矿池出现，会考虑集成进来。

首先将HPool的API Key输入，填写矿机名称，点击开始挖矿按钮，就可以挖矿了。

挖矿所使用的目录，就是硬盘界面中配置的机械硬盘目录。如果你不想指定的目录用来挖矿，只需要将左边的勾去掉即可。

### 自动开始挖矿
在挖矿界面左下方，有个自动开始挖矿的选项。勾选之后，软件在启动之后就会自动开始挖矿。

### 挖矿进程守护
挖矿程序有时会崩溃，或显示扫盘超时等问题。这时会自动重启挖矿程序以防止离线。

# 创建任务实战
## 创建并发任务，一直运行直到P满所有硬盘
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/create03.jpg)
最终目录选择自动，不指定数量。

使用以上配置，创建多条任务，即可实现多任务并发。
## 在指定硬盘中P指定数量的图
![image](https://gitee.com/devteamcn/chia-tools/raw/master/images/create04.jpg)
最终目录中选择目标硬盘。

如果要单任务按顺序P图，输入指定的数量即可。

如果要并发，指定1个数量，以相同的配置创建多个任务。
