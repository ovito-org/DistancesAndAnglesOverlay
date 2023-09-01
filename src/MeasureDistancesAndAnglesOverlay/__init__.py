#### Measure distances and angles overlay ####
# Viewport overlay to measure and display distances and angles between particles
# https://github.com/nnn911/DistancesAndAnglesOverlay for more information

from ovito.vis import *
from ovito.data import *
import numpy as np
from PySide6.QtCore import QRect
from ovito.qt_compat import QtGui
from traits.api import Float, Int, Range, List, Bool, Str
from ovito.traits import ColorTrait


# IMAGE = QtGui.QImage(1, 1, QtGui.QImage.Format_RGBA8888)
# IMAGECOLOR = (-1, -1, -1)


class MeasureDistancesAndAnglesOverlay(ViewportOverlayInterface):
    particle_ids = List(Int, label="Particle IDs")
    line_width = Float(3, label="Line width")
    line_color = ColorTrait((0.0, 0.0, 0.0), label="Line color")
    font_size = Float(0.05, label="Font size")
    text_color = ColorTrait((0.0, 0.0, 0.0), label="Text color")
    outline_width = Range(low=0, high=None, value=0, label="Outline width")
    outline_color = ColorTrait((1.0, 1.0, 1.0), label="Outline color")
    show_distances = Bool(True, label="Show distances")
    distance_label_format = Str("{:.3f}", label="Number format (distance)")
    # show_background = Bool(False, label="Background")
    # background_color = ColorTrait(value=(0, 0, 0), label="Background color")
    show_angles = Bool(True, label="Show angles")
    arc_distance = Range(low=0.0, high=100, value=20, label="Arc distance (%)")
    angle_format = Str("{:.1f} °", label="Number format (angles)")

    # def draw_background(self, canvas, pos, size, anchor):
    #     global IMAGE, IMAGECOLOR
    #     if IMAGECOLOR != self.background_color:
    #         IMAGE.fill(QtGui.QColor.fromRgbF(*self.background_color))
    #         IMAGECOLOR = self.background_color
    #         print("Updated background color")
    #     canvas.draw_image(IMAGE, pos=pos, size=size, anchor=anchor)

    def draw_single_step(
        self, data, canvas, painter, particle_index_a, particle_index_b
    ):
        screen_pos_proj = np.empty((2, 2))

        screen_pos_proj[0] = canvas.project_location(
            data.particles["Position"][particle_index_a]
        )
        screen_pos_proj[1] = canvas.project_location(
            data.particles["Position"][particle_index_b]
        )

        screen_pos_proj_pxl = screen_pos_proj * np.array(canvas.logical_size)
        text_pos = np.mean(screen_pos_proj, axis=0)
        if screen_pos_proj_pxl[1][0] > screen_pos_proj_pxl[0][0]:
            text_angle = np.pi - np.arctan2(
                screen_pos_proj_pxl[0][1] - screen_pos_proj_pxl[1][1],
                screen_pos_proj_pxl[0][0] - screen_pos_proj_pxl[1][0],
            )
        else:
            text_angle = np.pi - np.arctan2(
                screen_pos_proj_pxl[1][1] - screen_pos_proj_pxl[0][1],
                screen_pos_proj_pxl[1][0] - screen_pos_proj_pxl[0][0],
            )

        dist = data.cell.delta_vector(
            data.particles["Position"][particle_index_a],
            data.particles["Position"][particle_index_b],
        )

        # if self.show_background:
        #     self.draw_background(
        #         canvas,
        #         *canvas.text_bounds(
        #             f"{np.linalg.norm(dist) :.3g} Å",
        #             font_size=self.font_size,
        #             pos=text_pos,
        #             anchor="south",
        #             rotation=text_angle,
        #         ),
        #         "south west",
        #     )
        if self.show_distances:
            canvas.draw_text(
                self.distance_label_format.format(np.linalg.norm(dist)),
                font_size=self.font_size,
                color=self.text_color,
                outline_width=self.outline_width,
                outline_color=self.outline_color,
                pos=text_pos,
                anchor="south",
                rotation=text_angle,
            )

        screen_pos_painter = np.copy(screen_pos_proj)
        screen_pos_painter[:, 1] = 1 - screen_pos_proj[:, 1]
        screen_pos_painter *= np.array(canvas.logical_size)
        painter.drawLine(
            int(screen_pos_painter[0][0]),
            int(screen_pos_painter[0][1]),
            int(screen_pos_painter[1][0]),
            int(screen_pos_painter[1][1]),
        )

    def draw_single_angle(
        self,
        data,
        canvas,
        painter,
        particle_index_a,
        particle_index_b,
        particle_index_c,
    ):
        screen_pos_proj = np.empty((3, 2))

        vc = data.particles["Position"][particle_index_b]
        v1 = data.particles["Position"][particle_index_a]
        v2 = data.particles["Position"][particle_index_c]
        screen_pos_proj[0] = canvas.project_location(vc)
        screen_pos_proj[1] = canvas.project_location(v1)
        screen_pos_proj[2] = canvas.project_location(v2)

        screen_pos_painter = np.copy(screen_pos_proj)
        screen_pos_painter[:, 1] = 1 - screen_pos_proj[:, 1]
        screen_pos_painter *= np.array(canvas.logical_size)

        l1 = np.linalg.norm(screen_pos_painter[1] - screen_pos_painter[0])
        l2 = np.linalg.norm(screen_pos_painter[2] - screen_pos_painter[0])
        radius = np.min((l1, l2)) * self.arc_distance / 100.0

        bbox = QRect(
            screen_pos_painter[0, 0] - radius,
            screen_pos_painter[0, 1] - radius,
            radius * 2,
            radius * 2,
        )

        start_angle = 16 * np.rad2deg(
            2 * np.pi
            - np.arctan2(
                screen_pos_painter[1, 1] - screen_pos_painter[0, 1],
                screen_pos_painter[1, 0] - screen_pos_painter[0, 0],
            )
        )

        end_angle = 16 * np.rad2deg(
            2 * np.pi
            - np.arctan2(
                screen_pos_painter[2, 1] - screen_pos_painter[0, 1],
                screen_pos_painter[2, 0] - screen_pos_painter[0, 0],
            )
        )

        angle = end_angle - start_angle

        if (
            screen_pos_proj[0, 0] < screen_pos_proj[1, 0]
            or screen_pos_proj[0, 0] < screen_pos_proj[2, 0]
        ):
            flip = 1 if screen_pos_proj[1, 1] > screen_pos_proj[2, 1] else -1
            if np.abs(angle) > 180 * 16:
                painter.drawArc(bbox, start_angle, flip * (360 * 16 - np.abs(angle)))
            else:
                painter.drawArc(bbox, start_angle, angle)
        else:
            flip = 1 if screen_pos_proj[1, 1] < screen_pos_proj[2, 1] else -1
            if np.abs(angle) > 180 * 16:
                painter.drawArc(
                    bbox,
                    end_angle,
                    flip * (360 * 16 - np.abs(angle)),
                )
            else:
                painter.drawArc(bbox, end_angle, -angle)

        if screen_pos_proj[0, 0] < np.min(screen_pos_proj[1:, 0]):
            anchor = "east"
        elif screen_pos_proj[0, 1] > np.max(screen_pos_proj[1:, 1]):
            anchor = "south"
        elif screen_pos_proj[0, 0] > np.max(screen_pos_proj[1:, 0]):
            anchor = "west"
        elif screen_pos_proj[0, 1] < np.min(screen_pos_proj[1:, 1]):
            anchor = "north"
        else:
            anchor = "center"

        angle = np.arccos(
            np.dot(v2 - vc, v1 - vc)
            / (np.linalg.norm(v2 - vc) * np.linalg.norm(v1 - vc))
        )
        # if self.show_background:
        #     self.draw_background(
        #         canvas,
        #         *canvas.text_bounds(
        #             text,
        #             font_size=self.font_size,
        #             pos=screen_pos_proj[0],
        #             anchor=anchor,
        #         ),
        #         "south west",
        #     )
        canvas.draw_text(
            self.angle_format.format(np.rad2deg(angle)),
            font_size=self.font_size,
            color=self.text_color,
            outline_width=self.outline_width,
            outline_color=self.outline_color,
            pos=screen_pos_proj[0],
            anchor=anchor,
        )

    def render(
        self,
        canvas: ViewportOverlayInterface.Canvas,
        data: DataCollection,
        frame: int,
        **kwargs,
    ):
        if "Particle Identifier" not in data.particles:
            raise KeyError(
                "'Particle Identifier' particle property not found. Please add a 'Particle Identifier' particle property."
            )
        if len(np.unique(self.particle_ids)) < 2:
            raise ValueError(
                "At least 2 particle identifieres are required to show length."
            )

        with canvas.qt_painter() as painter:
            pen = QtGui.QPen(QtGui.QPen())
            pen.setWidth(self.line_width)
            pen.setColor(QtGui.QColor.fromRgbF(*self.line_color))
            painter.setPen(pen)

            for i in range(1, len(self.particle_ids)):
                if i == 1:
                    particle_index_a = np.where(
                        data.particles["Particle Identifier"]
                        == self.particle_ids[i - 1]
                    )[0][0]
                else:
                    particle_index_a = particle_index_b
                particle_index_b = np.where(
                    data.particles["Particle Identifier"] == self.particle_ids[i]
                )[0][0]

                self.draw_single_step(
                    data, canvas, painter, particle_index_a, particle_index_b
                )

            if not self.show_angles:
                return
            if len(np.unique(self.particle_ids)) < 3:
                raise ValueError(
                    "At least 3 distinct particle identifieres are required to show angles."
                )

            if self.particle_ids[0] == self.particle_ids[-1]:
                self.particle_ids.append(self.particle_ids[1])
            for i in range(2, len(self.particle_ids)):
                if i == 2:
                    particle_index_a = np.where(
                        data.particles["Particle Identifier"]
                        == self.particle_ids[i - 2]
                    )[0][0]
                else:
                    particle_index_a = particle_index_b
                if i == 2:
                    particle_index_b = np.where(
                        data.particles["Particle Identifier"]
                        == self.particle_ids[i - 1]
                    )[0][0]
                else:
                    particle_index_b = particle_index_c
                particle_index_c = np.where(
                    data.particles["Particle Identifier"] == self.particle_ids[i]
                )[0][0]
                self.draw_single_angle(
                    data,
                    canvas,
                    painter,
                    particle_index_a,
                    particle_index_b,
                    particle_index_c,
                )
