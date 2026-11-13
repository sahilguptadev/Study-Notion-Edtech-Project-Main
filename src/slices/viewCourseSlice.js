import { createSlice } from "@reduxjs/toolkit"

const initialState = {
  courseSectionData: [],
  courseEntireData: [],
  completedLectures: [],
  totalNoOfLectures: 0,
}

const viewCourseSlice = createSlice({
  name: "viewCourse",
  initialState,
  reducers: {
    setCourseSectionData: (state, action) => {
      state.courseSectionData = action.payload
    },
    setEntireCourseData: (state, action) => {
      state.courseEntireData = action.payload
    },
    setTotalNoOfLectures: (state, action) => {
      state.totalNoOfLectures = action.payload
    },
    setCompletedLectures: (state, action) => {
      state.completedLectures = action.payload
    },
    updateCompletedLectures: (state, action) => {
      state.completedLectures = [...state.completedLectures, action.payload]
    },
    // Clear the previously viewed course so a new course never renders stale data
    resetViewCourse: () => initialState,
  },
})

export const {
  setCourseSectionData,
  setEntireCourseData,
  setTotalNoOfLectures,
  setCompletedLectures,
  updateCompletedLectures,
  resetViewCourse,
} = viewCourseSlice.actions

export default viewCourseSlice.reducer
